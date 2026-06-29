"""Tests for deterministic mock ContextProviders."""

from __future__ import annotations

from parakeetnest.context import ContextRequest, ContextService, MeetingContext
from parakeetnest.context.providers import (
    KnowledgeBaseContextProvider,
    MacroContextProvider,
    MarketContextProvider,
    NewsContextProvider,
    PortfolioContextProvider,
)
from parakeetnest.market_data import MarketDataService, MockMarketDataProvider


SECTION_NAMES = (
    "market",
    "news",
    "filings",
    "portfolio",
    "macro",
    "knowledge_base",
)


def _populated_sections(context: MeetingContext) -> tuple[str, ...]:
    return tuple(
        section for section in SECTION_NAMES if getattr(context, section) is not None
    )


def _market_context_provider() -> MarketContextProvider:
    return MarketContextProvider(MarketDataService(MockMarketDataProvider()))


def test_providers_support_expected_requests() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    no_symbols = ContextRequest(question="Review market.", symbols=())

    assert _market_context_provider().supports(request) is True
    assert _market_context_provider().supports(no_symbols) is False
    assert NewsContextProvider().supports(request) is True
    assert NewsContextProvider().supports(no_symbols) is False

    assert PortfolioContextProvider().supports(request) is True
    assert PortfolioContextProvider().supports(
        ContextRequest(
            question="Review AMD without portfolio.",
            symbols=("AMD",),
            include_portfolio=False,
        )
    ) is False

    assert MacroContextProvider().supports(request) is True
    assert MacroContextProvider().supports(
        ContextRequest(
            question="Review AMD without macro.",
            symbols=("AMD",),
            include_macro=False,
        )
    ) is False

    assert KnowledgeBaseContextProvider().supports(request) is True
    assert KnowledgeBaseContextProvider().supports(
        ContextRequest(
            question="Review AMD without memory.",
            symbols=("AMD",),
            include_knowledge_base=False,
        )
    ) is False


def test_each_provider_contributes_only_its_own_section() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    providers = (
        (_market_context_provider(), ("market",)),
        (NewsContextProvider(), ("news",)),
        (PortfolioContextProvider(), ("portfolio",)),
        (MacroContextProvider(), ("macro",)),
        (KnowledgeBaseContextProvider(), ("knowledge_base",)),
    )

    for provider, expected_sections in providers:
        result = provider.build_context(request)

        assert result.provider_name == provider.provider_name
        assert result.partial_context.request == request
        assert result.partial_context.metadata.sources == (provider.provider_name,)
        assert _populated_sections(result.partial_context) == expected_sections


def test_providers_return_deterministic_values() -> None:
    request = ContextRequest(question="Review AMD and NVDA.", symbols=("AMD", "NVDA"))

    for provider in (
        _market_context_provider(),
        NewsContextProvider(),
        PortfolioContextProvider(),
        MacroContextProvider(),
        KnowledgeBaseContextProvider(),
    ):
        first = provider.build_context(request)
        second = provider.build_context(request)

        assert first == second


def test_mock_providers_work_with_context_service() -> None:
    request = ContextRequest(question="Review AMD and NVDA.", symbols=("AMD", "NVDA"))
    service = ContextService(
        providers=(
            _market_context_provider(),
            NewsContextProvider(),
            PortfolioContextProvider(),
            MacroContextProvider(),
            KnowledgeBaseContextProvider(),
        )
    )

    context = service.build_context(request)

    assert _populated_sections(context) == (
        "market",
        "news",
        "portfolio",
        "macro",
        "knowledge_base",
    )
    assert context.market is not None
    assert tuple(point.symbol for point in context.market.points) == ("AMD", "NVDA")
    assert context.news is not None
    assert tuple(item.symbol for item in context.news.items) == ("AMD", "NVDA")
    assert context.portfolio is not None
    assert tuple(position.symbol for position in context.portfolio.positions) == (
        "AMD",
        "NVDA",
    )
    assert context.macro is not None
    assert context.macro.summary == (
        "Mock macro backdrop is neutral-to-constructive for risk assets."
    )
    assert context.knowledge_base is not None
    assert context.knowledge_base.lessons_learned == (
        "Check memory before debating fresh catalysts.",
        "Separate durable thesis changes from single-quarter noise.",
    )
    assert context.metadata.sources == (
        "market_data",
        "mock_news",
        "mock_portfolio",
        "mock_macro",
        "mock_knowledge_base",
    )
    assert context.metadata.data_quality_notes == (
        "market_data.source=market_data_service",
        "mock_news.fixture=news",
        "mock_portfolio.fixture=portfolio",
        "mock_macro.fixture=macro",
        "mock_knowledge_base.fixture=knowledge_base",
    )


def test_context_service_output_is_deterministic_with_mock_providers() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    providers = (
        _market_context_provider(),
        NewsContextProvider(),
        PortfolioContextProvider(),
        MacroContextProvider(),
        KnowledgeBaseContextProvider(),
    )

    assert ContextService(providers).build_context(request) == ContextService(
        providers
    ).build_context(request)
