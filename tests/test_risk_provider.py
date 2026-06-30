"""Tests for the provider-neutral Risk Layer boundary."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.intelligence.risk import (
    RiskAssessment,
    RiskLevel,
    RiskProvider,
)


AS_OF_DATE = date(2026, 6, 30)


class RecordingRiskProvider:
    """Test double that satisfies the RiskProvider protocol."""

    def __init__(self) -> None:
        self.calls: list[tuple[str | None, date | None]] = []
        self.assessment = RiskAssessment(
            overall_level=RiskLevel.MODERATE,
            overall_score=0.5,
            as_of_date=AS_OF_DATE,
            source="recording_risk_provider",
        )

    def get_risk_assessment(
        self,
        *,
        subject: str | None = None,
        as_of_date: date | None = None,
    ) -> RiskAssessment:
        self.calls.append((subject, as_of_date))
        return self.assessment


def test_risk_provider_protocol_accepts_structural_implementation() -> None:
    """Providers should satisfy the contract by shape, not inheritance."""
    provider: RiskProvider = RecordingRiskProvider()

    assessment = provider.get_risk_assessment(
        subject="portfolio",
        as_of_date=AS_OF_DATE,
    )

    assert assessment.overall_level is RiskLevel.MODERATE
    assert provider.calls == [("portfolio", AS_OF_DATE)]


def test_risk_provider_signature_is_simple_and_provider_neutral() -> None:
    """The provider boundary should avoid vendor-specific dependencies."""
    signature = inspect.signature(RiskProvider.get_risk_assessment)

    assert list(signature.parameters) == ["self", "subject", "as_of_date"]
    assert signature.return_annotation == "RiskAssessment"


def test_risk_provider_module_has_no_provider_specific_imports() -> None:
    """The provider abstraction should not import upstream concrete providers."""
    forbidden_names = {
        "yahoo",
        "yfinance",
        "requests",
        "httpx",
        "sqlite",
        "database",
        "sec",
        "macro",
        "valuation",
        "llm",
        "recommendation",
        "trading",
    }
    forbidden_modules = {
        "requests",
        "httpx",
        "yfinance",
        "aiohttp",
        "sqlite3",
    }

    source = inspect.getsource(sys.modules[RiskProvider.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider: RiskProvider = RecordingRiskProvider()
    assessment = provider.get_risk_assessment(as_of_date=AS_OF_DATE)

    assert isinstance(assessment, RiskAssessment)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_risk_package_exports_provider_boundary() -> None:
    """The package should expose the RiskProvider boundary."""
    import parakeetnest.intelligence.risk as risk

    assert risk.RiskProvider is RiskProvider
