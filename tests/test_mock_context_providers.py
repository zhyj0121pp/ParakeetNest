"""Tests for deterministic mock ContextProviders."""

from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.context import ContextRequest, ContextService, MeetingContext
from parakeetnest.context.providers import (
    KnowledgeBaseContextProvider,
    MacroContextProvider,
    MarketContextProvider,
    NewsContextProvider,
    PortfolioContextProvider,
)
from parakeetnest.market_data import MarketDataService, MockMarketDataProvider
from parakeetnest.macro import MacroDataService, MockMacroDataProvider
from parakeetnest.news import MockNewsProvider, NewsService
from parakeetnest.portfolio import (
    MockPortfolioProvider,
    PortfolioCashBalance,
    PortfolioHolding,
    PortfolioSnapshot,
)


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


def _news_context_provider() -> NewsContextProvider:
    return NewsContextProvider(NewsService(MockNewsProvider()))


def _macro_context_provider() -> MacroContextProvider:
    return MacroContextProvider(MacroDataService(MockMacroDataProvider()))


def _portfolio_context_provider() -> PortfolioContextProvider:
    return PortfolioContextProvider(MockPortfolioProvider())


def test_providers_support_expected_requests() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    no_symbols = ContextRequest(question="Review market.", symbols=())

    assert _market_context_provider().supports(request) is True
    assert _market_context_provider().supports(no_symbols) is False
    assert _news_context_provider().supports(request) is True
    assert _news_context_provider().supports(no_symbols) is False

    assert _portfolio_context_provider().supports(request) is True
    assert _portfolio_context_provider().supports(no_symbols) is True
    assert _portfolio_context_provider().supports(
        ContextRequest(
            question="Review AMD without portfolio.",
            symbols=("AMD",),
            include_portfolio=False,
        )
    ) is False

    assert _macro_context_provider().supports(request) is True
    assert _macro_context_provider().supports(
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
        (_news_context_provider(), ("news",)),
        (_portfolio_context_provider(), ("portfolio",)),
        (_macro_context_provider(), ("macro",)),
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
        _news_context_provider(),
        _portfolio_context_provider(),
        _macro_context_provider(),
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
            _news_context_provider(),
            _portfolio_context_provider(),
            _macro_context_provider(),
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
        "NVDA",
        "MSFT",
        "AAPL",
        "MU",
        "CRDO",
        "RKLB",
        "OKLO",
    )
    assert context.portfolio.cash_balance == 2500.0
    assert context.portfolio.total_value == 36708.2
    assert tuple(
        allocation.category
        for allocation in context.portfolio.allocation_by_symbol[:2]
    ) == ("NVDA", "MSFT")
    assert context.macro is not None
    assert context.macro.summary is None
    assert context.macro.indicators[:3] == (
        "Interest Rates:",
        "Federal Funds Rate (fed_funds_rate, US, monthly, percent): "
        "4 as of 2026-06-30",
        "10-Year Treasury Yield (treasury_10y_yield, US, monthly, percent): "
        "4.08 as of 2026-06-30",
    )
    assert context.knowledge_base is not None
    assert context.knowledge_base.lessons_learned == (
        "Check memory before debating fresh catalysts.",
        "Separate durable thesis changes from single-quarter noise.",
    )
    assert context.metadata.sources == (
        "market_data",
        "news",
        "portfolio",
        "macro",
        "mock_knowledge_base",
    )
    assert context.metadata.data_quality_notes == (
        "market_data.source=market_data_service",
        "news.source=news_service",
        "portfolio.account_id=mock-main",
        "portfolio.source=portfolio_provider",
        "macro.source=macro_data_service",
        "mock_knowledge_base.fixture=knowledge_base",
    )


def test_context_service_output_is_deterministic_with_mock_providers() -> None:
    request = ContextRequest(question="Review AMD.", symbols=("AMD",))
    providers = (
        _market_context_provider(),
        _news_context_provider(),
        _portfolio_context_provider(),
        _macro_context_provider(),
        KnowledgeBaseContextProvider(),
    )

    assert ContextService(providers).build_context(request) == ContextService(
        providers
    ).build_context(request)


def test_portfolio_context_provider_uses_portfolio_provider_snapshot() -> None:
    as_of = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    portfolio_provider = MockPortfolioProvider(
        snapshots={
            "paper": PortfolioSnapshot(
                account_id="paper",
                as_of=as_of,
                holdings=(
                    PortfolioHolding(
                        symbol="XYZ",
                        name="Xylophone Yield Zone",
                        quantity=2,
                        average_cost=40,
                        current_price=50,
                    ),
                ),
                cash_balances=(PortfolioCashBalance(amount=25),),
            )
        }
    )

    result = PortfolioContextProvider(
        portfolio_provider,
        account_id="paper",
    ).build_context(ContextRequest(question="Review portfolio.", symbols=()))

    portfolio = result.partial_context.portfolio
    assert portfolio is not None
    assert portfolio.cash_balance == 25.0
    assert portfolio.total_value == 125.0
    assert portfolio.positions[0].symbol == "XYZ"
    assert portfolio.allocation_by_symbol[0].percent == 0.8
