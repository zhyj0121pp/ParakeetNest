"""Tests for the provider-neutral economic regime service."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.macro import (
    MacroCategory,
    MacroFrequency,
    MacroIndicator,
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
    MacroUnit,
)
from parakeetnest.regime import (
    EconomicRegime,
    EconomicRegimeService,
    EconomicRegimeSnapshot,
    RegimeConfidence,
)


AS_OF_DATE = date(2026, 6, 30)


class FakeMacroService:
    """Macro service test double that records snapshot requests."""

    def __init__(self, snapshot: MacroSnapshot | None = None) -> None:
        self.snapshot = snapshot or macro_snapshot(
            {
                "gdp_growth": 2.6,
                "cpi_yoy": 2.8,
                "unemployment_rate": 4.2,
                "yield_curve_spread": 0.8,
                "fed_funds_rate": 3.5,
            },
        )
        self.snapshot_calls: list[tuple[list[str], date | None]] = []

    def get_snapshot(
        self,
        indicator_ids: list[str],
        as_of_date: date | None = None,
    ) -> MacroSnapshot:
        """Record the service-layer request and return a neutral snapshot."""
        self.snapshot_calls.append((indicator_ids, as_of_date))
        return self.snapshot


class FailingMacroService:
    """Macro service test double that simulates upstream failure."""

    def get_snapshot(
        self,
        indicator_ids: list[str],
        as_of_date: date | None = None,
    ) -> MacroSnapshot:
        """Raise a data access error."""
        raise RuntimeError("macro service unavailable")


class SpyClassifier:
    """Classifier test double that records invocation arguments."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object | None]] = []

    def classify(
        self,
        *,
        real_gdp_growth: object | None = None,
        inflation_rate: object | None = None,
        unemployment_rate: object | None = None,
        yield_curve_spread: object | None = None,
        policy_rate: object | None = None,
        credit_spread: object | None = None,
        as_of_date: date | None = None,
    ) -> EconomicRegimeSnapshot:
        """Record classifier inputs and return a deterministic snapshot."""
        self.calls.append(
            {
                "real_gdp_growth": real_gdp_growth,
                "inflation_rate": inflation_rate,
                "unemployment_rate": unemployment_rate,
                "yield_curve_spread": yield_curve_spread,
                "policy_rate": policy_rate,
                "credit_spread": credit_spread,
                "as_of_date": as_of_date,
            }
        )
        return EconomicRegimeSnapshot(
            regime=EconomicRegime.EXPANSION,
            confidence=RegimeConfidence.HIGH,
            as_of_date=as_of_date or AS_OF_DATE,
            source="spy_classifier",
        )


def macro_snapshot(values: dict[str, float | None]) -> MacroSnapshot:
    """Build a provider-neutral macro snapshot for service tests."""
    return MacroSnapshot(
        as_of_date=AS_OF_DATE,
        series=[
            MacroSeries(
                indicator=MacroIndicator(
                    indicator_id=indicator_id,
                    name=indicator_id.replace("_", " ").title(),
                    category=MacroCategory.OTHER,
                    frequency=MacroFrequency.MONTHLY,
                    unit=MacroUnit.PERCENT,
                ),
                observations=[
                    MacroObservation(period=date(2026, 5, 31), value=None),
                    MacroObservation(period=AS_OF_DATE, value=value),
                ],
            )
            for indicator_id, value in values.items()
        ],
    )


def test_get_current_regime_successfully_classifies_macro_snapshot() -> None:
    """The service should fetch normalized macro data and return classifier output."""
    macro_service = FakeMacroService()
    service = EconomicRegimeService(macro_service)

    snapshot = service.get_current_regime(as_of_date=AS_OF_DATE)

    assert snapshot.regime is EconomicRegime.EXPANSION
    assert snapshot.confidence is RegimeConfidence.HIGH
    assert snapshot.as_of_date == AS_OF_DATE
    assert macro_service.snapshot_calls == [
        (
            [
                "gdp_growth",
                "cpi_yoy",
                "unemployment_rate",
                "yield_curve_spread",
                "fed_funds_rate",
                "credit_spread",
            ],
            AS_OF_DATE,
        )
    ]


def test_classify_snapshot_handles_missing_macro_data_gracefully() -> None:
    """Missing core values should flow to the classifier without service failure."""
    service = EconomicRegimeService(FakeMacroService())
    snapshot = service.classify_snapshot(
        macro_snapshot({"gdp_growth": 2.1, "yield_curve_spread": 0.4}),
    )

    assert snapshot.regime is EconomicRegime.UNKNOWN
    assert snapshot.confidence is RegimeConfidence.UNKNOWN
    assert snapshot.as_of_date == AS_OF_DATE


def test_service_uses_dependency_injected_macro_service_and_classifier() -> None:
    """The service should be driven by injected abstractions."""
    macro_service = FakeMacroService()
    classifier = SpyClassifier()
    service = EconomicRegimeService(macro_service, classifier=classifier)

    snapshot = service.get_current_regime(as_of_date=AS_OF_DATE)

    assert snapshot.source == "spy_classifier"
    assert macro_service.snapshot_calls
    assert classifier.calls == [
        {
            "real_gdp_growth": 2.6,
            "inflation_rate": 2.8,
            "unemployment_rate": 4.2,
            "yield_curve_spread": 0.8,
            "policy_rate": 3.5,
            "credit_spread": None,
            "as_of_date": AS_OF_DATE,
        }
    ]


def test_classify_snapshot_invokes_classifier_with_custom_indicator_map() -> None:
    """Callers should be able to adapt neutral macro IDs without providers."""
    classifier = SpyClassifier()
    service = EconomicRegimeService(
        FakeMacroService(),
        classifier=classifier,
        indicator_map={
            "real_gdp_growth": "real_gdp",
            "inflation_rate": "inflation",
            "unemployment_rate": "jobless_rate",
        },
    )

    snapshot = service.classify_snapshot(
        macro_snapshot(
            {
                "real_gdp": 1.8,
                "inflation": 2.4,
                "jobless_rate": 5.2,
            }
        )
    )

    assert snapshot.source == "spy_classifier"
    assert classifier.calls == [
        {
            "real_gdp_growth": 1.8,
            "inflation_rate": 2.4,
            "unemployment_rate": 5.2,
            "yield_curve_spread": None,
            "policy_rate": None,
            "credit_spread": None,
            "as_of_date": AS_OF_DATE,
        }
    ]


def test_get_current_regime_returns_unknown_when_macro_service_fails() -> None:
    """Upstream macro failures should return a neutral regime snapshot."""
    service = EconomicRegimeService(FailingMacroService())

    snapshot = service.get_current_regime(as_of_date=AS_OF_DATE)

    assert snapshot.regime is EconomicRegime.UNKNOWN
    assert snapshot.confidence is RegimeConfidence.UNKNOWN
    assert snapshot.as_of_date == AS_OF_DATE
    assert snapshot.source == "economic_regime_service"
    assert snapshot.summary == (
        "Unable to retrieve normalized macro data for regime classification."
    )


def test_regime_service_is_exported_from_package() -> None:
    """The regime package should expose the public service boundary."""
    import parakeetnest.regime as regime

    assert regime.EconomicRegimeService is EconomicRegimeService


def test_regime_service_is_provider_independent() -> None:
    """The service should not import or expose provider-specific models."""
    forbidden_names = {
        "fred",
        "yahoo",
        "bea",
        "bls",
        "requests",
        "httpx",
        "sqlite",
        "database",
        "llm",
    }
    forbidden_modules = {"requests", "httpx", "yfinance", "aiohttp", "sqlite3"}
    source = inspect.getsource(sys.modules[EconomicRegimeService.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    service = EconomicRegimeService(FakeMacroService())
    snapshot = service.get_current_regime(as_of_date=AS_OF_DATE)

    assert isinstance(snapshot, EconomicRegimeSnapshot)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)
