"""Tests for the application bootstrap container."""

from pathlib import Path

import pytest

from parakeetnest.app import ParakeetNestApp, create_app, create_test_app
from parakeetnest.committee.memory import (
    CommitteeMemoryService,
    MemoryQuery,
    MemoryType,
    SQLiteCommitteeMemoryRepository,
)
from parakeetnest.config import AppConfig
from parakeetnest.context import ContextRequest
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.financials import MockFinancialStatementProvider
from parakeetnest.intelligence.context import MockInvestmentIntelligenceService
from parakeetnest.intelligence.market_breadth import (
    MarketBreadthCalculator,
    MarketBreadthContextProvider,
    MarketBreadthService,
    MockMarketBreadthProvider,
)
from parakeetnest.llm import MockLLMProvider
from parakeetnest.news import NewsQuery
from parakeetnest.sec import EdgarSecFilingProvider, MockSecFilingProvider
from parakeetnest.watchlist import (
    InMemoryWatchlistRepository,
    WatchlistContextProvider,
    WatchlistIntelligenceService,
)


def test_create_app_returns_working_application(tmp_path: Path) -> None:
    """The app factory should centralize wiring for a runnable meeting."""
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        result = app.meeting_service.run(
            question="Should I watch POET?",
            ticker="POET",
        )
        app.commit()
    finally:
        app.close()

    assert isinstance(app, ParakeetNestApp)
    assert result.status.value == "completed"
    assert result.result_json is not None
    assert result.result_json["action"] == "watch"


def test_create_test_app_uses_mock_llm_provider() -> None:
    """The test factory should use an isolated database and mock LLM provider."""
    app = create_test_app()
    try:
        assert app.config.environment == "test"
        assert isinstance(app.llm_provider, MockLLMProvider)
    finally:
        app.close()


def test_create_app_wires_sqlite_committee_memory_service(tmp_path: Path) -> None:
    """The app factory should create durable committee memory when it owns a session."""
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        assert isinstance(app.memory_service, CommitteeMemoryService)
        assert isinstance(
            app.memory_service._repository,
            SQLiteCommitteeMemoryRepository,
        )
        assert app.agent_runtime.memory_service is app.memory_service
        assert app.committee_orchestrator.memory_service is app.memory_service
    finally:
        app.close()


def test_create_app_loads_watchlist_seed_items(tmp_path: Path) -> None:
    """The app factory should seed the in-memory watchlist when configured."""
    seed_path = tmp_path / "watchlist.json"
    seed_path.write_text(
        """
        [
          {
            "symbol": "NVDA",
            "theme": "AI infrastructure",
            "reason": "Track AI accelerator demand",
            "priority": "high"
          }
        ]
        """,
        encoding="utf-8",
    )
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            watchlist_seed_path=seed_path,
            enabled_context_provider_ids=("watchlist",),
        )
    )
    try:
        context = app.context_service.build_context(
            ContextRequest(question="Review watchlist.", symbols=())
        )
    finally:
        app.close()

    assert context.watchlist is not None
    assert tuple(item.symbol for item in context.watchlist.items) == ("NVDA",)
    assert context.watchlist.items[0].summary == (
        "Track AI accelerator demand. Theme: AI infrastructure."
    )


def test_create_test_app_runs_mock_investment_intelligence_end_to_end() -> None:
    """The test app should pass mock investment intelligence into agent prompts."""
    app = create_test_app()
    try:
        result = app.meeting_service.run(
            question="Should I watch NVDA?",
            ticker="NVDA",
        )
    finally:
        app.close()

    assert result.status.value == "completed"
    assert isinstance(
        app.investment_intelligence_context_service,
        MockInvestmentIntelligenceService,
    )
    assert isinstance(app.llm_provider, MockLLMProvider)
    assert app.llm_provider.requests
    first_prompt = app.llm_provider.requests[0].prompt
    assert "Investment intelligence context:" in first_prompt
    assert "# Investment Intelligence Context" in first_prompt
    assert "## Market Health" in first_prompt
    assert "- Symbol: NVDA" in first_prompt


def test_app_runtime_reads_memory_context_from_sqlite_service(
    tmp_path: Path,
) -> None:
    """Agent prompts should read prior memories through the SQLite-backed service."""
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        assert app.memory_service is not None
        meeting = app.meeting_repository.create_meeting(
            "Should we add to NVDA?",
            "NVDA",
        )
        app.memory_service.save_agent_observation(
            meeting_id=str(meeting.id),
            agent_id="xixi",
            ticker="NVDA",
            content="SQLite memory says prior margin risk was manageable.",
        )
        app.commit()

        app.committee_orchestrator.run(
            meeting.id,
            "Should we add to NVDA?",
            "NVDA",
            app.context_service.build_context(
                ContextRequest(question="Should we add to NVDA?", symbols=("NVDA",))
            ),
        )
    finally:
        app.close()

    first_prompt = app.llm_provider.requests[0].prompt
    assert "Relevant Committee Memories:" in first_prompt
    assert "SQLite memory says prior margin risk was manageable." in first_prompt


def test_completed_app_meeting_writes_back_to_sqlite_memory_repository(
    tmp_path: Path,
) -> None:
    """Completed meetings should write durable memories through app composition."""
    database_path = tmp_path / "app.sqlite3"
    app = create_app(AppConfig(database_path=database_path))
    try:
        result = app.meeting_service.run(
            question="Should I watch NVDA?",
            ticker="NVDA",
        )
        app.commit()
        meeting_id = result.meeting_id
    finally:
        app.close()

    reopened_app = create_app(AppConfig(database_path=database_path))
    try:
        assert reopened_app.memory_service is not None
        memories = reopened_app.memory_service.search(
            MemoryQuery(meeting_id=str(meeting_id), limit=20)
        )
    finally:
        reopened_app.close()

    memory_types = {memory.memory.memory_type for memory in memories}
    assert MemoryType.MEETING_SUMMARY in memory_types
    assert MemoryType.DECISION in memory_types
    assert MemoryType.AGENT_OBSERVATION in memory_types


def test_create_app_can_disable_context_provider_before_service_creation(
    tmp_path: Path,
) -> None:
    """Provider config should be applied before ContextService receives providers."""
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            disabled_context_provider_ids=("news",),
        )
    )
    try:
        registrations = {
            registration.provider_id: registration.enabled
            for registration in app.context_provider_registry.list_registrations()
        }
        context = app.context_service.build_context(
            ContextRequest(question="Review AMD.", symbols=("AMD",))
        )
    finally:
        app.close()

    assert registrations["news"] is False
    assert registrations["market_data"] is True
    assert context.news is None
    assert context.market is not None


def test_create_app_wires_configured_news_service(tmp_path: Path) -> None:
    """The app factory should resolve the configured News Layer provider."""
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            news={"provider": "mock"},
        )
    )
    try:
        articles = app.news_service.get_news(NewsQuery(symbols=["POET"]))
    finally:
        app.close()

    assert len(articles) == 1
    assert articles[0].provider == "mock"
    assert articles[0].symbols == ["POET"]


def test_create_app_wires_news_context_provider_through_news_service(
    tmp_path: Path,
) -> None:
    """The context pipeline should receive news through NewsService."""
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            news={"provider": "mock"},
        )
    )
    try:
        context = app.context_service.build_context(
            ContextRequest(question="Review POET.", symbols=("POET",))
        )
    finally:
        app.close()

    assert context.news is not None
    assert context.news.source == "news"
    assert len(context.news.items) == 1
    assert context.news.items[0].symbol == "POET"


def test_create_app_defaults_to_mock_sec_filing_provider(tmp_path: Path) -> None:
    """The app factory should keep deterministic SEC filings as the default."""
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        context = app.context_service.build_context(
            ContextRequest(question="Review AAPL.", symbols=("AAPL",))
        )
    finally:
        app.close()

    assert isinstance(app.sec_filing_service._provider, MockSecFilingProvider)
    assert context.filings is not None
    assert context.filings.source == "sec_filings"
    assert context.filings.items[0].source == "mock"


def test_create_app_allows_mock_sec_filings_with_blank_edgar_user_agent(
    tmp_path: Path,
) -> None:
    """Blank SEC EDGAR identity should be ignored while mock filings are selected."""
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            sec_filings={
                "provider": "mock",
                "sec_edgar_user_agent": "   ",
            },
        )
    )
    try:
        provider = app.sec_filing_service._provider
    finally:
        app.close()

    assert isinstance(provider, MockSecFilingProvider)


def test_create_app_wires_sec_edgar_provider_when_configured(tmp_path: Path) -> None:
    """The app factory should resolve SEC EDGAR without making live requests."""
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            sec_filings={
                "provider": "sec_edgar",
                "sec_edgar_user_agent": "ParakeetNest tests test@example.com",
            },
        )
    )
    try:
        provider = app.sec_filing_service._provider
    finally:
        app.close()

    assert isinstance(provider, EdgarSecFilingProvider)


def test_create_app_wires_financial_statement_context_provider(
    tmp_path: Path,
) -> None:
    """The context pipeline should receive financials through the service."""
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        provider = app.financial_statement_service._provider_source
        context = app.context_service.build_context(
            ContextRequest(question="Review AMD.", symbols=("AMD",))
        )
    finally:
        app.close()

    registrations = {
        registration.provider_id
        for registration in app.context_provider_registry.list_registrations()
    }
    assert "financial_statements" in registrations
    assert isinstance(provider, MockFinancialStatementProvider)
    assert context.financials is not None
    assert context.financials.source == "financial_statements"
    assert [item.period_type for item in context.financials.items] == [
        "annual",
        "quarterly",
        "ttm",
    ]


def test_create_app_wires_market_breadth_layer(tmp_path: Path) -> None:
    """The app factory should register the Market Breadth dependency graph."""
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        registrations = {
            registration.provider_id: registration.provider
            for registration in app.context_provider_registry.list_registrations()
        }
        provider = registrations["market_breadth"]
        context = app.context_service.build_context(
            ContextRequest(question="Review market conditions.", symbols=("SPY",))
        )
    finally:
        app.close()

    assert isinstance(app.market_breadth_service, MarketBreadthService)
    assert isinstance(provider, MarketBreadthContextProvider)
    assert provider._service is app.market_breadth_service
    assert isinstance(app.market_breadth_service._provider, MockMarketBreadthProvider)
    assert isinstance(app.market_breadth_service._calculator, MarketBreadthCalculator)
    assert context.market_breadth is not None
    assert context.market_breadth.source == "market_breadth"
    assert context.market_breadth.universe == "SP500"
    assert context.market_breadth.breadth_regime == "healthy"
    assert app.market_breadth_service._provider.calls == ["SP500"]


def test_create_app_wires_watchlist_context_provider(tmp_path: Path) -> None:
    """The context pipeline should receive watchlist insights through the service."""
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        registrations = {
            registration.provider_id: registration.provider
            for registration in app.context_provider_registry.list_registrations()
        }
        provider = registrations["watchlist"]
        context = app.context_service.build_context(
            ContextRequest(question="Prepare watchlist.", symbols=())
        )
    finally:
        app.close()

    assert isinstance(app.watchlist_intelligence_service, WatchlistIntelligenceService)
    assert isinstance(
        app.watchlist_intelligence_service._repository,
        InMemoryWatchlistRepository,
    )
    assert isinstance(provider, WatchlistContextProvider)
    assert provider._watchlist_intelligence_service is app.watchlist_intelligence_service
    assert context.watchlist is not None
    assert context.watchlist.source == "watchlist"
    assert context.watchlist.items == ()


def test_create_app_rejects_sec_edgar_without_user_agent(tmp_path: Path) -> None:
    """SEC EDGAR requires an explicit app identity before bootstrap succeeds."""
    with pytest.raises(
        ConfigurationError,
        match="sec_filings.sec_edgar_user_agent",
    ):
        create_app(
            AppConfig(
                database_path=tmp_path / "app.sqlite3",
                sec_filings={
                    "provider": "sec_edgar",
                    "sec_edgar_user_agent": "   ",
                },
            )
        )
