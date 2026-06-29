"""Tests for ContextService assembly behavior."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from parakeetnest.context import (
    ContextMetadata,
    ContextProviderResult,
    ContextRequest,
    ContextService,
    MarketDataPoint,
    MarketSnapshot,
    MeetingContext,
    NewsContext,
    NewsItem,
)


class RecordingProvider:
    """Simple provider test double with deterministic responses."""

    def __init__(
        self,
        provider_name: str,
        partial_context: MeetingContext,
        *,
        supported: bool = True,
        metadata: dict[str, str] | None = None,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
    ) -> None:
        self.provider_name = provider_name
        self.partial_context = partial_context
        self.supported = supported
        self.metadata = metadata or {}
        self.warnings = warnings
        self.errors = errors
        self.support_requests: list[ContextRequest] = []
        self.build_requests: list[ContextRequest] = []

    def supports(self, request: ContextRequest) -> bool:
        self.support_requests.append(request)
        return self.supported

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        self.build_requests.append(request)
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=self.partial_context,
            metadata=self.metadata,
            warnings=self.warnings,
            errors=self.errors,
        )


def _partial(
    request: ContextRequest,
    provider_name: str,
    *,
    market: MarketSnapshot | None = None,
    news: NewsContext | None = None,
    warnings: tuple[str, ...] = (),
    data_quality_notes: tuple[str, ...] = (),
) -> MeetingContext:
    return MeetingContext(
        request=request,
        metadata=ContextMetadata(
            generated_at=datetime(2026, 6, 29, 13, 0, tzinfo=UTC),
            sources=(provider_name,),
            data_quality_notes=data_quality_notes,
            warnings=warnings,
        ),
        market=market,
        news=news,
    )


def test_multiple_providers_are_merged_correctly() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    market = MarketSnapshot(
        source="market_provider",
        points=(MarketDataPoint(symbol="AMD", source="market_provider", price=175.0),),
    )
    news = NewsContext(
        source="news_provider",
        items=(NewsItem(title="AMD expands roadmap", source="news_provider"),),
    )
    service = ContextService(
        providers=(
            RecordingProvider(
                "market_provider",
                _partial(request, "market_provider", market=market),
            ),
            RecordingProvider("news_provider", _partial(request, "news_provider", news=news)),
        )
    )

    context = service.build_context(request)

    assert context.request == request
    assert context.market == market
    assert context.news == news
    assert context.metadata.sources == ("market_provider", "news_provider")


def test_unsupported_providers_are_skipped() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    unsupported = RecordingProvider(
        "unsupported",
        _partial(
            request,
            "unsupported",
            market=MarketSnapshot(source="unsupported"),
        ),
        supported=False,
    )
    supported = RecordingProvider(
        "supported",
        _partial(
            request,
            "supported",
            news=NewsContext(source="supported"),
        ),
    )
    service = ContextService(providers=(unsupported, supported))

    context = service.build_context(request)

    assert unsupported.support_requests == [request]
    assert unsupported.build_requests == []
    assert supported.build_requests == [request]
    assert context.market is None
    assert context.news == NewsContext(source="supported")


def test_provider_ordering_is_deterministic_for_duplicate_sections() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    first_market = MarketSnapshot(source="first")
    second_market = MarketSnapshot(source="second")
    service = ContextService(
        providers=(
            RecordingProvider(
                "first",
                _partial(request, "first", market=first_market),
            ),
            RecordingProvider(
                "second",
                _partial(request, "second", market=second_market),
            ),
        )
    )

    context = service.build_context(request)

    assert context.market == first_market
    assert context.metadata.sources == ("first", "second")
    assert context.metadata.warnings == (
        "second skipped market: section already populated",
    )


def test_metadata_aggregation_works() -> None:
    request = ContextRequest(
        question="Review AMD.",
        symbols=("AMD",),
        as_of=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
    )
    partial = _partial(
        request,
        "market_provider",
        market=MarketSnapshot(source="market_provider"),
        warnings=("stale quote",),
        data_quality_notes=("quotes are delayed",),
    )
    provider = RecordingProvider(
        "market_provider",
        partial,
        metadata={"fixture": "market", "priority": "primary"},
        warnings=("provider warning",),
    )
    service = ContextService(providers=(provider,))

    context = service.build_context(request)

    assert context.metadata.generated_at == request.as_of
    assert context.metadata.sources == ("market_provider",)
    assert context.metadata.warnings == ("stale quote", "provider warning")
    assert context.metadata.data_quality_notes == (
        "quotes are delayed",
        "market_provider.fixture=market",
        "market_provider.priority=primary",
    )


def test_metadata_sources_and_data_quality_notes_merge_deterministically() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    first = RecordingProvider(
        "first",
        _partial(
            request,
            "first_source",
            market=MarketSnapshot(source="first"),
            data_quality_notes=("first note",),
        ),
        metadata={"zeta": "last", "alpha": "first"},
    )
    second = RecordingProvider(
        "second",
        _partial(
            request,
            "second_source",
            news=NewsContext(source="second"),
            data_quality_notes=("second note",),
        ),
        metadata={"beta": "middle", "alpha": "again"},
    )
    service = ContextService(providers=(first, second))

    context = service.build_context(request)

    assert context.metadata.sources == ("first_source", "second_source")
    assert context.metadata.data_quality_notes == (
        "first note",
        "first.alpha=first",
        "first.zeta=last",
        "second note",
        "second.alpha=again",
        "second.beta=middle",
    )


def test_provider_errors_do_not_stop_context_assembly() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    failing = RecordingProvider(
        "filings_provider",
        _partial(request, "filings_provider"),
        errors=("SEC fixture unavailable",),
    )
    succeeding_news = NewsContext(source="news_provider")
    succeeding = RecordingProvider(
        "news_provider",
        replace(
            _partial(request, "news_provider"),
            news=succeeding_news,
        ),
    )
    service = ContextService(providers=(failing, succeeding))

    context = service.build_context(request)

    assert failing.build_requests == [request]
    assert succeeding.build_requests == [request]
    assert context.news == succeeding_news
    assert context.metadata.warnings == (
        "filings_provider error: SEC fixture unavailable",
    )
