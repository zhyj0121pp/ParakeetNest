"""Tests for the provider-neutral Momentum service."""

from __future__ import annotations

import inspect
import sys
from datetime import date

from parakeetnest.intelligence.momentum import (
    MockMomentumProvider,
    MomentumCalculator,
    MomentumInputs,
    MomentumRegime,
    MomentumService,
    MomentumSnapshot,
    ReversalRisk,
)


AS_OF_DATE = date(2026, 6, 30)


def momentum_inputs(
    *,
    symbol: str = "AAPL",
    as_of: date = AS_OF_DATE,
) -> MomentumInputs:
    """Build one provider-neutral momentum input set for service tests."""
    return MomentumInputs(
        symbol=symbol,
        as_of=as_of,
        price_change_1m=0.04,
        price_change_3m=0.11,
        price_change_6m=0.22,
        relative_strength=84,
        trend_strength=0.72,
    )


def momentum_snapshot(
    *,
    symbol: str = "AAPL",
    as_of: date = AS_OF_DATE,
    momentum_score: float = 0.87,
) -> MomentumSnapshot:
    """Build one provider-neutral momentum snapshot for service tests."""
    return MomentumSnapshot(
        symbol=symbol,
        as_of=as_of,
        price_change_1m=0.04,
        price_change_3m=0.11,
        price_change_6m=0.22,
        relative_strength=84,
        trend_strength=0.72,
        momentum_score=momentum_score,
        momentum_regime=MomentumRegime.STRONG_UPTREND,
        reversal_risk=ReversalRisk.LOW,
        confidence=0.91,
        evidence=("calculator-owned evidence",),
    )


class RecordingProvider:
    """Provider test double that records raw input requests."""

    def __init__(self, inputs: MomentumInputs) -> None:
        self.inputs = inputs
        self.calls: list[tuple[str, date | None]] = []

    def get_momentum_inputs(
        self,
        symbol: str,
        *,
        as_of: date | None = None,
    ) -> MomentumInputs:
        self.calls.append((symbol, as_of))
        return self.inputs


class RecordingCalculator:
    """Calculator test double that records service orchestration."""

    def __init__(self, snapshot: MomentumSnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[MomentumInputs] = []

    def calculate(self, inputs: MomentumInputs) -> MomentumSnapshot:
        self.calls.append(inputs)
        return self.snapshot


def test_service_calls_provider() -> None:
    """The service should retrieve raw inputs from the provider."""
    inputs = momentum_inputs()
    provider = RecordingProvider(inputs)
    service = MomentumService(provider, RecordingCalculator(momentum_snapshot()))

    service.get_snapshot("AAPL", as_of=AS_OF_DATE)

    assert provider.calls == [("AAPL", AS_OF_DATE)]


def test_service_calls_calculator() -> None:
    """The service should pass provider inputs to the calculator."""
    inputs = momentum_inputs()
    calculator = RecordingCalculator(momentum_snapshot())
    service = MomentumService(RecordingProvider(inputs), calculator)

    service.get_snapshot("AAPL", as_of=AS_OF_DATE)

    assert calculator.calls == [inputs]


def test_returned_snapshot_matches_calculator_output() -> None:
    """The service should return the exact calculator snapshot."""
    expected = momentum_snapshot(momentum_score=0.43)
    service = MomentumService(
        RecordingProvider(momentum_inputs()),
        RecordingCalculator(expected),
    )

    result = service.get_snapshot("AAPL", as_of=AS_OF_DATE)

    assert result is expected


def test_dependency_injection_works() -> None:
    """The service should accept provider and calculator duck types."""
    inputs = momentum_inputs(symbol="MSFT")
    expected = momentum_snapshot(symbol="MSFT", momentum_score=0.62)
    provider = RecordingProvider(inputs)
    calculator = RecordingCalculator(expected)
    service = MomentumService(provider, calculator)

    result = service.get_snapshot(" msft ", as_of=AS_OF_DATE)

    assert provider.calls == [(" msft ", AS_OF_DATE)]
    assert calculator.calls == [inputs]
    assert result is expected


def test_mock_provider_works_with_real_calculator() -> None:
    """The mock provider should compose with the real calculator."""
    inputs = momentum_inputs(symbol="NVDA")
    provider = MockMomentumProvider(inputs={"NVDA": inputs})
    service = MomentumService(provider, MomentumCalculator())

    result = service.get_snapshot("NVDA", as_of=AS_OF_DATE)

    assert provider.calls == [("NVDA", AS_OF_DATE)]
    assert result == MomentumCalculator().calculate(inputs)


def test_service_has_no_duplicated_business_logic() -> None:
    """The service should not score, classify, or generate evidence."""
    forbidden_names = {
        "calculate_score",
        "classify_momentum",
        "classify_reversal_risk",
        "confidence_for",
        "evidence_for",
        "momentum_score",
        "momentum_regime",
        "reversal_risk",
        "confidence",
        "evidence",
    }
    source = inspect.getsource(sys.modules[MomentumService.__module__])

    assert all(name not in source for name in forbidden_names)


def test_momentum_package_exports_service() -> None:
    """The package should expose the public service boundary."""
    import parakeetnest.intelligence.momentum as momentum

    assert momentum.MomentumService is MomentumService
