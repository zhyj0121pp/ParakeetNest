"""Application bootstrap and dependency wiring."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from parakeetnest.committee.agents import (
    ChairmanAgent,
    DongdongAgent,
    XixiAgent,
    YoyoAgent,
)
from parakeetnest.committee.memory import (
    CommitteeMemoryService,
    SQLiteCommitteeMemoryRepository,
)
from parakeetnest.committee.orchestrator import CommitteeMeetingOrchestrator
from parakeetnest.committee.runtime import AgentRuntime, PromptRenderer
from parakeetnest.config import AppConfig
from parakeetnest.context.providers import (
    FinancialStatementContextProvider,
    KnowledgeBaseContextProvider,
    MacroContextProvider,
    MarketContextProvider,
    NewsContextProvider,
    PortfolioContextProvider,
    SecFilingContextProvider,
    WatchlistContextProvider,
)
from parakeetnest.context.registry import ContextProviderRegistry
from parakeetnest.context.service import ContextService
from parakeetnest.database import (
    CommitteeMeetingRepository,
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.financials import (
    FinancialStatementService,
    create_financial_statement_provider_registry,
)
from parakeetnest.intelligence.market_breadth import (
    MarketBreadthCalculator,
    MarketBreadthContextProvider,
    MarketBreadthService,
    MockMarketBreadthProvider,
)
from parakeetnest.intelligence.context import MockInvestmentIntelligenceService
from parakeetnest.intelligence.sector_rotation import (
    MockSectorRotationProvider,
    SectorRotationService,
)
from parakeetnest.intelligence.sector_rotation.context_provider import (
    SectorRotationContextProvider,
)
from parakeetnest.llm import LLMProvider, create_llm_provider_registry
from parakeetnest.market_data import (
    MarketDataService,
    create_market_data_provider_registry,
)
from parakeetnest.macro import MacroDataService, MockMacroDataProvider
from parakeetnest.news import NewsService, create_news_provider_registry
from parakeetnest.portfolio import create_portfolio_provider_registry
from parakeetnest.portfolio.provider import PortfolioProvider
from parakeetnest.regime import EconomicRegimeService
from parakeetnest.regime.context_provider import EconomicRegimeContextProvider
from parakeetnest.sec import SecFilingService, create_sec_filing_provider_registry
from parakeetnest.services import (
    InvestmentIntelligenceContextService,
    MeetingService,
)
from parakeetnest.watchlist import (
    InMemoryWatchlistRepository,
    WatchlistSeedLoader,
    WatchlistIntelligenceService,
)


@dataclass
class ParakeetNestApp:
    """Application container for ParakeetNest services."""

    config: AppConfig
    meeting_repository: CommitteeMeetingRepository
    prompt_renderer: PromptRenderer
    context_provider_registry: ContextProviderRegistry
    context_service: ContextService
    news_service: NewsService
    macro_data_service: MacroDataService
    economic_regime_service: EconomicRegimeService
    sector_rotation_service: SectorRotationService
    market_breadth_service: MarketBreadthService
    investment_intelligence_context_service: InvestmentIntelligenceContextService
    sec_filing_service: SecFilingService
    financial_statement_service: FinancialStatementService
    watchlist_intelligence_service: WatchlistIntelligenceService
    llm_provider: LLMProvider
    memory_service: CommitteeMemoryService | None
    agent_runtime: AgentRuntime
    committee_orchestrator: CommitteeMeetingOrchestrator
    meeting_service: MeetingService
    session: Session = field(repr=False)

    def commit(self) -> None:
        """Commit pending application persistence work."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback pending application persistence work."""
        self.session.rollback()

    def close(self) -> None:
        """Close application-owned resources."""
        self.session.close()


def create_app(config: AppConfig | None = None) -> ParakeetNestApp:
    """Create the configured ParakeetNest application container."""
    resolved_config = config or AppConfig()
    engine = create_database_engine(resolved_config.resolved_database_url())
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()

    meeting_repository = CommitteeMeetingRepository(session)
    memory_repository = SQLiteCommitteeMemoryRepository(session)
    memory_service = CommitteeMemoryService(memory_repository)
    prompt_renderer = PromptRenderer(prompt_dir=resolved_config.prompt_dir)
    news_service = _create_news_service(resolved_config)
    macro_data_service = _create_macro_data_service()
    economic_regime_service = EconomicRegimeService(macro_data_service)
    sector_rotation_service = _create_sector_rotation_service()
    market_breadth_service = _create_market_breadth_service()
    investment_intelligence_context_service = MockInvestmentIntelligenceService()
    sec_filing_service = _create_sec_filing_service(resolved_config)
    financial_statement_service = _create_financial_statement_service(resolved_config)
    watchlist_intelligence_service = _create_watchlist_intelligence_service(
        resolved_config
    )
    context_provider_registry = _create_context_provider_registry(
        resolved_config,
        news_service,
        macro_data_service,
        economic_regime_service,
        sector_rotation_service,
        market_breadth_service,
        sec_filing_service,
        financial_statement_service,
        watchlist_intelligence_service,
    )
    context_service = ContextService(
        providers=context_provider_registry.resolve_enabled_providers()
    )
    llm_provider = _create_llm_provider(resolved_config)
    agent_runtime = AgentRuntime(
        llm_provider=llm_provider,
        model=resolved_config.llm.model,
        temperature=resolved_config.llm.temperature,
        prompt_renderer=prompt_renderer,
        memory_service=memory_service,
    )
    committee_orchestrator = CommitteeMeetingOrchestrator(
        repository=meeting_repository,
        agents=(
            XixiAgent(),
            DongdongAgent(),
            YoyoAgent(),
            ChairmanAgent(),
        ),
        agent_runtime=agent_runtime,
        memory_service=memory_service,
    )
    meeting_service = MeetingService(
        repository=meeting_repository,
        orchestrator=committee_orchestrator,
        context_service=context_service,
        investment_intelligence_context_service=investment_intelligence_context_service,
    )

    return ParakeetNestApp(
        config=resolved_config,
        meeting_repository=meeting_repository,
        prompt_renderer=prompt_renderer,
        context_provider_registry=context_provider_registry,
        context_service=context_service,
        news_service=news_service,
        macro_data_service=macro_data_service,
        economic_regime_service=economic_regime_service,
        sector_rotation_service=sector_rotation_service,
        market_breadth_service=market_breadth_service,
        investment_intelligence_context_service=investment_intelligence_context_service,
        sec_filing_service=sec_filing_service,
        financial_statement_service=financial_statement_service,
        watchlist_intelligence_service=watchlist_intelligence_service,
        llm_provider=llm_provider,
        memory_service=memory_service,
        agent_runtime=agent_runtime,
        committee_orchestrator=committee_orchestrator,
        meeting_service=meeting_service,
        session=session,
    )


def create_test_app() -> ParakeetNestApp:
    """Create an isolated test application container."""
    return create_app(
        AppConfig(
            database_url="sqlite:///:memory:",
            llm_provider="mock",
            environment="test",
        )
    )


def _create_llm_provider(config: AppConfig) -> LLMProvider:
    llm_provider_registry = create_llm_provider_registry()
    return llm_provider_registry.resolve(config.llm)


def _create_news_service(config: AppConfig) -> NewsService:
    news_provider_registry = create_news_provider_registry()
    news_provider = news_provider_registry.get(config.news.provider)
    return NewsService(news_provider)


def _create_macro_data_service() -> MacroDataService:
    return MacroDataService(MockMacroDataProvider())


def _create_sector_rotation_service() -> SectorRotationService:
    return SectorRotationService(MockSectorRotationProvider())


def _create_market_breadth_service() -> MarketBreadthService:
    return MarketBreadthService(
        MockMarketBreadthProvider(),
        calculator=MarketBreadthCalculator(),
    )


def _create_sec_filing_service(config: AppConfig) -> SecFilingService:
    sec_user_agent = _normalize_optional_string(config.sec_filings.user_agent)
    provider_id = config.sec_filings.provider.strip().lower()
    if provider_id in {"edgar", "sec_edgar"}:
        if sec_user_agent is None:
            raise ConfigurationError(
                "SEC filing provider 'edgar' requires sec.user_agent "
                "or sec_filings.user_agent."
            )

    sec_filing_provider_registry = create_sec_filing_provider_registry(
        user_agent=sec_user_agent,
        timeout=config.sec_filings.timeout,
    )
    sec_filing_provider = sec_filing_provider_registry.get(config.sec_filings.provider)
    return SecFilingService(sec_filing_provider)


def _create_financial_statement_service(config: AppConfig) -> FinancialStatementService:
    financial_statement_provider_registry = (
        create_financial_statement_provider_registry()
    )
    financial_statement_provider = financial_statement_provider_registry.get_provider(
        config.financials.provider
    )
    return FinancialStatementService(financial_statement_provider)


def _create_watchlist_intelligence_service(
    config: AppConfig,
) -> WatchlistIntelligenceService:
    seed_items = ()
    if config.watchlist_seed_path is not None:
        seed_items = WatchlistSeedLoader().load(config.watchlist_seed_path)
    return WatchlistIntelligenceService(InMemoryWatchlistRepository(seed_items))


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized_value = value.strip()
    return normalized_value or None


def _create_context_provider_registry(
    config: AppConfig,
    news_service: NewsService,
    macro_data_service: MacroDataService,
    economic_regime_service: EconomicRegimeService,
    sector_rotation_service: SectorRotationService,
    market_breadth_service: MarketBreadthService,
    sec_filing_service: SecFilingService,
    financial_statement_service: FinancialStatementService,
    watchlist_intelligence_service: WatchlistIntelligenceService,
) -> ContextProviderRegistry:
    registry = ContextProviderRegistry()
    market_data_provider_registry = create_market_data_provider_registry()
    market_data_provider = market_data_provider_registry.resolve(config.market_data)
    market_data_service = MarketDataService(market_data_provider)
    registry.register("market_data", MarketContextProvider(market_data_service))
    registry.register("news", NewsContextProvider(news_service))
    registry.register("sec_filings", SecFilingContextProvider(sec_filing_service))
    registry.register(
        "financial_statements",
        FinancialStatementContextProvider(financial_statement_service),
    )
    registry.register(
        "portfolio",
        PortfolioContextProvider(
            _create_portfolio_provider(config),
            account_id=_portfolio_account_id(config),
        ),
    )
    registry.register("macro", MacroContextProvider(macro_data_service))
    registry.register(
        "economic_regime",
        EconomicRegimeContextProvider(economic_regime_service),
    )
    registry.register(
        "sector_rotation",
        SectorRotationContextProvider(sector_rotation_service),
    )
    registry.register(
        "market_breadth",
        MarketBreadthContextProvider(market_breadth_service),
    )
    registry.register(
        "watchlist",
        WatchlistContextProvider(watchlist_intelligence_service),
    )
    registry.register("mock_knowledge_base", KnowledgeBaseContextProvider())
    _apply_context_provider_config(registry, config)
    return registry


def _apply_context_provider_config(
    registry: ContextProviderRegistry,
    config: AppConfig,
) -> None:
    provider_ids = {
        registration.provider_id for registration in registry.list_registrations()
    }

    if config.enabled_context_provider_ids is not None:
        _raise_for_unknown_context_provider_ids(
            provider_ids,
            config.enabled_context_provider_ids,
        )
        enabled_provider_ids = set(config.enabled_context_provider_ids)
        for registration in registry.list_registrations():
            registry.set_enabled(
                registration.provider_id,
                registration.provider_id in enabled_provider_ids,
            )

    _raise_for_unknown_context_provider_ids(
        provider_ids,
        config.disabled_context_provider_ids,
    )
    for provider_id in config.disabled_context_provider_ids:
        registry.disable(provider_id)


def _raise_for_unknown_context_provider_ids(
    provider_ids: set[str],
    configured_provider_ids: tuple[str, ...],
) -> None:
    unknown_provider_ids = sorted(set(configured_provider_ids) - provider_ids)
    if unknown_provider_ids:
        joined_provider_ids = ", ".join(unknown_provider_ids)
        raise KeyError(f"Unknown context provider(s): {joined_provider_ids}")


def _create_portfolio_provider(config: AppConfig) -> PortfolioProvider:
    portfolio_provider_registry = create_portfolio_provider_registry()
    return portfolio_provider_registry.resolve(config.portfolio)


def _portfolio_account_id(config: AppConfig) -> str:
    if config.portfolio.account_id is not None:
        account_id = config.portfolio.account_id.strip()
        if account_id:
            return account_id
    if config.portfolio.provider.strip().lower() == "mock":
        return "mock-main"
    return "default"
