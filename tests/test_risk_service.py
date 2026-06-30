"""Tests for the provider-neutral Risk service."""

from __future__ import annotations

from datetime import date

import pytest

from parakeetnest.intelligence.risk import (
    RiskAssessment,
    RiskCalculator,
    RiskCategory,
    RiskLevel,
    RiskService,
    RiskSignal,
)


AS_OF_DATE = date(2026, 6, 30)


class RecordingRiskProvider:
    """Risk provider test double that records signal requests."""

    def __init__(self, signals: list[RiskSignal] | None = None) -> None:
        self.signals = signals or []
        self.calls: list[date | None] = []

    def get_risk_signals(
        self,
        *,
        as_of_date: date | None = None,
    ) -> list[RiskSignal]:
        self.calls.append(as_of_date)
        return self.signals


class RecordingCalculator:
    """Risk calculator test double that records service orchestration."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[RiskSignal], date | None]] = []
        self.assessment = RiskAssessment(
            overall_level=RiskLevel.MODERATE,
            overall_score=0.4,
            as_of_date=AS_OF_DATE,
            source="recording_calculator",
        )

    def calculate(
        self,
        signals: list[RiskSignal],
        *,
        as_of_date: date | None = None,
    ) -> RiskAssessment:
        self.calls.append((signals, as_of_date))
        return self.assessment


class FailingProvider:
    """Provider test double that simulates upstream failure."""

    def get_risk_signals(
        self,
        *,
        as_of_date: date | None = None,
    ) -> list[RiskSignal]:
        raise RuntimeError("risk provider unavailable")


class FailingCalculator:
    """Calculator test double that simulates deterministic calculation failure."""

    def calculate(
        self,
        signals: list[RiskSignal],
        *,
        as_of_date: date | None = None,
    ) -> RiskAssessment:
        raise RuntimeError("risk calculation failed")


def signal() -> RiskSignal:
    """Build one provider-neutral risk signal for service tests."""
    return RiskSignal(
        category=RiskCategory.MARKET,
        level=RiskLevel.MODERATE,
        score=0.4,
        label="Market risk",
        description="Market conditions are mixed.",
        evidence=("breadth is mixed",),
    )


def test_service_delegates_provider_signals_to_calculator() -> None:
    """The service should orchestrate provider signals into the calculator."""
    signals = [signal()]
    provider = RecordingRiskProvider(signals=signals)
    calculator = RecordingCalculator()
    service = RiskService(provider, calculator)

    assessment = service.get_risk_assessment(as_of_date=AS_OF_DATE)

    assert assessment is calculator.assessment
    assert provider.calls == [AS_OF_DATE]
    assert calculator.calls == [(signals, AS_OF_DATE)]


def test_empty_provider_signals_work() -> None:
    """Empty provider output should flow into the calculator."""
    provider = RecordingRiskProvider()
    service = RiskService(provider, RiskCalculator())

    assessment = service.get_risk_assessment(as_of_date=AS_OF_DATE)

    assert assessment.overall_level is RiskLevel.LOW
    assert assessment.overall_score == 0.0
    assert assessment.signals == []
    assert assessment.as_of_date == AS_OF_DATE
    assert assessment.source == "risk_calculator"


def test_provider_exception_propagates() -> None:
    """The service should not hide provider failures."""
    service = RiskService(FailingProvider(), RecordingCalculator())

    with pytest.raises(RuntimeError, match="risk provider unavailable"):
        service.get_risk_assessment(as_of_date=AS_OF_DATE)


def test_calculator_exception_propagates() -> None:
    """The service should not hide calculator failures."""
    service = RiskService(RecordingRiskProvider(), FailingCalculator())

    with pytest.raises(RuntimeError, match="risk calculation failed"):
        service.get_risk_assessment(as_of_date=AS_OF_DATE)


def test_as_of_date_forwarded_correctly() -> None:
    """The requested date should be forwarded to provider and calculator."""
    provider = RecordingRiskProvider()
    calculator = RecordingCalculator()
    service = RiskService(provider, calculator)

    service.get_risk_assessment(as_of_date=AS_OF_DATE)

    assert provider.calls == [AS_OF_DATE]
    assert calculator.calls == [([], AS_OF_DATE)]


def test_risk_package_exports_service() -> None:
    """The risk package should expose the public service boundary."""
    import parakeetnest.intelligence.risk as risk

    assert risk.RiskService is RiskService
