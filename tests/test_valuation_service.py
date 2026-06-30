"""Tests for the provider-neutral valuation service."""

from __future__ import annotations

from datetime import date

import pytest

from parakeetnest.valuation import (
    ValuationCalculator,
    ValuationConfidence,
    ValuationInput,
    ValuationMethod,
    ValuationMetric,
    ValuationService,
    ValuationSnapshot,
)


class SpyValuationCalculator:
    """Calculator test double that records service delegation."""

    def __init__(self) -> None:
        self.calls: list[ValuationInput] = []
        self.snapshot = ValuationSnapshot(
            symbol="AMD",
            as_of_date=date(2026, 6, 29),
            fiscal_period="TTM",
            metrics={ValuationMetric.PE_RATIO: 40.0},
            data_sources=["normalized inputs"],
            calculation_notes=["calculated by spy"],
            confidence=ValuationConfidence.MEDIUM,
        )

    def calculate(self, valuation_input: ValuationInput) -> ValuationSnapshot:
        """Record the input and return a prepared snapshot."""
        self.calls.append(valuation_input)
        return self.snapshot


def test_create_snapshot_delegates_to_calculator_once() -> None:
    """The service should create snapshots through its calculator dependency."""
    calculator = SpyValuationCalculator()
    service = ValuationService(calculator)
    valuation_input = ValuationInput(
        symbol="amd",
        method=ValuationMethod.HISTORICAL_MULTIPLES,
        as_of_date=date(2026, 6, 29),
        metrics={ValuationMetric.MARKET_CAP: 1_000.0},
        assumptions={"net_income": 25.0},
    )

    snapshot = service.create_snapshot(valuation_input)

    assert snapshot is calculator.snapshot
    assert calculator.calls == [valuation_input]


def test_create_snapshot_uses_default_calculator() -> None:
    """The default service should produce calculator-backed snapshots."""
    service = ValuationService()
    valuation_input = ValuationInput(
        symbol="nvda",
        method=ValuationMethod.HISTORICAL_MULTIPLES,
        as_of_date=date(2026, 6, 29),
        metrics={ValuationMetric.MARKET_CAP: 3_000.0},
        assumptions={
            "revenue": 100.0,
            "net_income": 30.0,
        },
        confidence=ValuationConfidence.HIGH,
    )

    snapshot = service.create_snapshot(valuation_input)

    assert snapshot.symbol == "NVDA"
    assert snapshot.as_of_date == date(2026, 6, 29)
    assert snapshot.confidence is ValuationConfidence.HIGH
    assert snapshot.metrics[ValuationMetric.PE_RATIO] == pytest.approx(100.0)
    assert snapshot.metrics[ValuationMetric.PS_RATIO] == pytest.approx(30.0)


def test_valuation_service_is_exported_from_package() -> None:
    """The valuation package should expose the service boundary."""
    assert ValuationService().__class__ is ValuationService
    assert isinstance(ValuationService()._calculator, ValuationCalculator)
