"""Tests for ValuationContextProvider service-backed behavior."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from parakeetnest.context import (
    ContextRequest,
    MeetingContextPromptRenderer,
    UnsupportedContextRequestError,
)
from parakeetnest.context.providers import ValuationContextProvider
from parakeetnest.valuation import (
    ValuationConfidence,
    ValuationInput,
    ValuationMethod,
    ValuationMetric,
    ValuationSnapshot,
)


class RecordingValuationService:
    """Valuation service test double that records normalized inputs."""

    def __init__(
        self,
        snapshots_by_symbol: dict[str, ValuationSnapshot] | None = None,
    ) -> None:
        self.snapshots_by_symbol = snapshots_by_symbol or {}
        self.calls: list[ValuationInput] = []

    def create_snapshot(self, valuation_input: ValuationInput) -> ValuationSnapshot:
        self.calls.append(valuation_input)
        return self.snapshots_by_symbol.get(
            valuation_input.symbol,
            ValuationSnapshot(
                symbol=valuation_input.symbol,
                as_of_date=valuation_input.as_of_date,
                fiscal_period=valuation_input.fiscal_period,
                metrics={ValuationMetric.PE_RATIO: None},
                data_sources=valuation_input.data_sources,
                calculation_notes=valuation_input.calculation_notes,
                confidence=valuation_input.confidence,
            ),
        )


def test_valuation_context_provider_supports_symbol_requests_only() -> None:
    provider = ValuationContextProvider(RecordingValuationService())

    assert provider.supports(ContextRequest("Review AMD.", ("AMD",))) is True
    assert provider.supports(ContextRequest("Review the market.", ())) is False


def test_valuation_context_provider_builds_context_from_service_snapshots() -> None:
    as_of = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
    service = RecordingValuationService(
        {
            "AMD": ValuationSnapshot(
                symbol="AMD",
                as_of_date=date(2026, 6, 29),
                fiscal_period="TTM",
                metrics={
                    ValuationMetric.PE_RATIO: 35.0,
                    ValuationMetric.PS_RATIO: 8.5,
                    ValuationMetric.FREE_CASH_FLOW_YIELD: None,
                },
                calculation_notes=["Calculated from normalized inputs."],
                confidence=ValuationConfidence.MEDIUM,
                data_sources=["market snapshot", "financial statements"],
            )
        }
    )
    request = ContextRequest(question="Review AMD.", symbols=("AMD",), as_of=as_of)

    result = ValuationContextProvider(service).build_context(request)

    assert result.provider_name == "valuation"
    assert result.metadata == {"source": "valuation_service"}
    assert len(service.calls) == 1
    assert service.calls[0].symbol == "AMD"
    assert service.calls[0].method is ValuationMethod.HISTORICAL_MULTIPLES
    assert service.calls[0].as_of_date == date(2026, 6, 29)

    assert result.partial_context.valuation is not None
    assert result.partial_context.valuation.source == "valuation"
    assert result.partial_context.valuation.fetched_at == as_of
    item = result.partial_context.valuation.items[0]
    assert item.symbol == "AMD"
    assert item.as_of_date == date(2026, 6, 29)
    assert item.fiscal_period == "TTM"
    assert item.metrics == {
        "pe_ratio": 35.0,
        "ps_ratio": 8.5,
        "free_cash_flow_yield": None,
    }
    assert item.calculation_notes == ("Calculated from normalized inputs.",)
    assert item.confidence == "medium"
    assert item.data_sources == ("market snapshot", "financial statements")


def test_valuation_context_provider_accepts_custom_input_builder() -> None:
    service = RecordingValuationService()
    request = ContextRequest(
        question="Review NVDA.",
        symbols=("nvda",),
        as_of=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
    )

    def build_input(symbol: str, context_request: ContextRequest) -> ValuationInput:
        assert symbol == "nvda"
        assert context_request is request
        return ValuationInput(
            symbol=symbol,
            method=ValuationMethod.OWNER_EARNINGS,
            as_of_date=date(2026, 6, 29),
            fiscal_period="FY2026",
            metrics={ValuationMetric.MARKET_CAP: 3000.0},
            assumptions={"net_income": 100.0},
            data_sources=["fixture"],
            calculation_notes=["Prepared by test builder."],
            confidence=ValuationConfidence.HIGH,
        )

    result = ValuationContextProvider(
        service,
        input_builder=build_input,
    ).build_context(request)

    assert len(service.calls) == 1
    assert service.calls[0].symbol == "NVDA"
    assert service.calls[0].method is ValuationMethod.OWNER_EARNINGS
    assert service.calls[0].metrics == {ValuationMetric.MARKET_CAP: 3000.0}
    assert result.partial_context.valuation is not None
    assert result.partial_context.valuation.items[0].data_sources == ("fixture",)


def test_valuation_context_provider_is_provider_neutral() -> None:
    service = RecordingValuationService(
        {
            "AMD": ValuationSnapshot(
                symbol="AMD",
                as_of_date=date(2026, 6, 29),
                metrics={ValuationMetric.PE_RATIO: 35.0},
            )
        }
    )
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))

    result = ValuationContextProvider(service).build_context(request)

    assert result.partial_context.valuation is not None
    item = result.partial_context.valuation.items[0]
    assert not isinstance(item, ValuationSnapshot)
    assert "yahoo" not in repr(result).lower()
    assert "sec" not in repr(result).lower()


def test_valuation_context_provider_renders_snapshots() -> None:
    as_of = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
    service = RecordingValuationService(
        {
            "AMD": ValuationSnapshot(
                symbol="AMD",
                as_of_date=date(2026, 6, 29),
                fiscal_period="TTM",
                metrics={ValuationMetric.PE_RATIO: 35.0},
                calculation_notes=["Calculated from normalized inputs."],
                confidence=ValuationConfidence.MEDIUM,
                data_sources=["market snapshot"],
            )
        }
    )
    request = ContextRequest(question="Review AMD.", symbols=("AMD",), as_of=as_of)
    result = ValuationContextProvider(service).build_context(request)

    rendered = MeetingContextPromptRenderer().render(result.partial_context)

    assert "## Valuation" in rendered
    assert "- AMD: as_of_date=2026-06-29" in rendered
    assert "metrics=pe_ratio=35.0" in rendered
    assert "calculation_notes=Calculated from normalized inputs." in rendered
    assert "confidence=medium" in rendered
    assert "data_sources=market snapshot" in rendered


def test_valuation_context_provider_handles_multiple_symbols() -> None:
    service = RecordingValuationService()
    request = ContextRequest(
        "Review AMD and NVDA.",
        ("AMD", "NVDA"),
        as_of=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
    )

    result = ValuationContextProvider(service).build_context(request)

    assert [call.symbol for call in service.calls] == ["AMD", "NVDA"]
    assert result.partial_context.valuation is not None
    assert [item.symbol for item in result.partial_context.valuation.items] == [
        "AMD",
        "NVDA",
    ]


def test_valuation_context_provider_rejects_requests_without_symbols() -> None:
    service = RecordingValuationService()
    provider = ValuationContextProvider(service)
    request = ContextRequest(question="Review the market.", symbols=())

    with pytest.raises(UnsupportedContextRequestError):
        provider.build_context(request)

    assert service.calls == []
