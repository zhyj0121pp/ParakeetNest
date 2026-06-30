"""Tests for the provider-neutral Momentum Layer boundary."""

from __future__ import annotations

import inspect
import sys
from dataclasses import fields
from datetime import date

from parakeetnest.intelligence.momentum import (
    MockMomentumProvider,
    MomentumInputs,
    MomentumProvider,
)


AS_OF_DATE = date(2026, 6, 30)


class RecordingMomentumProvider:
    """Test double that satisfies the MomentumProvider protocol."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, date | None]] = []
        self.inputs = MomentumInputs(
            symbol="AAPL",
            as_of=AS_OF_DATE,
            price_change_1m=0.04,
            price_change_3m=0.11,
            price_change_6m=0.22,
            relative_strength=84,
            trend_strength=0.72,
        )

    def get_momentum_inputs(
        self,
        symbol: str,
        *,
        as_of: date | None = None,
    ) -> MomentumInputs:
        self.calls.append((symbol, as_of))
        return self.inputs


def test_momentum_provider_accepts_structural_implementation() -> None:
    """Providers should satisfy the contract by shape, not inheritance."""
    provider: MomentumProvider = RecordingMomentumProvider()

    inputs = provider.get_momentum_inputs("AAPL", as_of=AS_OF_DATE)

    assert inputs.symbol == "AAPL"
    assert inputs.as_of == AS_OF_DATE
    assert provider.calls == [("AAPL", AS_OF_DATE)]


def test_momentum_provider_signature_is_simple_and_provider_neutral() -> None:
    """The provider boundary should avoid vendor-specific dependencies."""
    signature = inspect.signature(MomentumProvider.get_momentum_inputs)

    assert list(signature.parameters) == ["self", "symbol", "as_of"]
    assert signature.return_annotation == "MomentumInputs"


def test_momentum_inputs_are_raw_provider_neutral_fields() -> None:
    """Provider inputs should not contain calculator-owned outputs."""
    field_names = {field.name for field in fields(MomentumInputs)}

    assert field_names == {
        "symbol",
        "as_of",
        "price_change_1m",
        "price_change_3m",
        "price_change_6m",
        "relative_strength",
        "trend_strength",
    }
    assert "momentum_score" not in field_names
    assert "momentum_regime" not in field_names
    assert "reversal_risk" not in field_names


def test_momentum_provider_module_has_no_provider_specific_imports() -> None:
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

    source = inspect.getsource(sys.modules[MomentumProvider.__module__]).lower()

    for module_name in forbidden_modules:
        sys.modules.pop(module_name, None)

    provider: MomentumProvider = RecordingMomentumProvider()
    inputs = provider.get_momentum_inputs("AAPL", as_of=AS_OF_DATE)

    assert isinstance(inputs, MomentumInputs)
    assert all(name not in source for name in forbidden_names)
    assert forbidden_modules.isdisjoint(sys.modules)


def test_mock_provider_returns_deterministic_raw_inputs() -> None:
    """The mock provider should not require network access or vendor payloads."""
    provider = MockMomentumProvider()

    inputs = provider.get_momentum_inputs(" aapl ")

    assert inputs.symbol == "AAPL"
    assert inputs.as_of == AS_OF_DATE
    assert inputs.price_change_1m == 0.043
    assert inputs.price_change_3m == 0.118
    assert inputs.price_change_6m == 0.247
    assert inputs.relative_strength == 82.5
    assert inputs.trend_strength == 0.76
    assert provider.calls == [(" aapl ", None)]


def test_mock_provider_multiple_calls_return_identical_results() -> None:
    """Default mock inputs should be repeatable across calls."""
    provider = MockMomentumProvider()

    first = provider.get_momentum_inputs("MSFT")
    second = provider.get_momentum_inputs("MSFT")

    assert first == second
    assert provider.calls == [("MSFT", None), ("MSFT", None)]


def test_mock_provider_can_return_injected_inputs() -> None:
    """Tests and local callers should be able to inject fixed momentum inputs."""
    injected = MomentumInputs(
        symbol="NVDA",
        as_of=AS_OF_DATE,
        price_change_1m=0.07,
        price_change_3m=0.18,
        price_change_6m=0.31,
        relative_strength=91,
        trend_strength=0.84,
    )
    provider = MockMomentumProvider(inputs={"nvda": injected})

    inputs = provider.get_momentum_inputs("NVDA", as_of=AS_OF_DATE)

    assert inputs is injected
    assert provider.calls == [("NVDA", AS_OF_DATE)]


def test_momentum_package_exports_provider_boundary() -> None:
    """The package should expose provider and mock provider boundaries."""
    import parakeetnest.intelligence.momentum as momentum

    assert momentum.MomentumProvider is MomentumProvider
    assert momentum.MomentumInputs is MomentumInputs
    assert momentum.MockMomentumProvider is MockMomentumProvider
