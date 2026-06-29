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
from parakeetnest.committee.orchestrator import CommitteeMeetingOrchestrator
from parakeetnest.committee.runtime import AgentRuntime, PromptRenderer
from parakeetnest.config import AppConfig
from parakeetnest.context.providers import (
    KnowledgeBaseContextProvider,
    MacroContextProvider,
    MarketContextProvider,
    NewsContextProvider,
    PortfolioContextProvider,
)
from parakeetnest.context.registry import ContextProviderRegistry
from parakeetnest.context.service import ContextService
from parakeetnest.database import (
    CommitteeMeetingRepository,
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from parakeetnest.llm import LLMProvider, MockLLMProvider
from parakeetnest.market_data import (
    MarketDataService,
    create_market_data_provider_registry,
)
from parakeetnest.services import MeetingService


@dataclass
class ParakeetNestApp:
    """Application container for ParakeetNest services."""

    config: AppConfig
    meeting_repository: CommitteeMeetingRepository
    prompt_renderer: PromptRenderer
    context_provider_registry: ContextProviderRegistry
    context_service: ContextService
    llm_provider: LLMProvider
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
    prompt_renderer = PromptRenderer(prompt_dir=resolved_config.prompt_dir)
    context_provider_registry = _create_context_provider_registry(resolved_config)
    context_service = ContextService(
        providers=context_provider_registry.resolve_enabled_providers()
    )
    llm_provider = _create_llm_provider(resolved_config)
    agent_runtime = AgentRuntime(
        llm_provider=llm_provider,
        model="mock-committee",
        prompt_renderer=prompt_renderer,
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
    )
    meeting_service = MeetingService(
        repository=meeting_repository,
        orchestrator=committee_orchestrator,
        context_service=context_service,
    )

    return ParakeetNestApp(
        config=resolved_config,
        meeting_repository=meeting_repository,
        prompt_renderer=prompt_renderer,
        context_provider_registry=context_provider_registry,
        context_service=context_service,
        llm_provider=llm_provider,
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
    if config.llm_provider == "mock":
        return MockLLMProvider()
    raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")


def _create_context_provider_registry(config: AppConfig) -> ContextProviderRegistry:
    registry = ContextProviderRegistry()
    market_data_provider_registry = create_market_data_provider_registry()
    market_data_provider = market_data_provider_registry.resolve(
        config.market_data.provider
    )
    market_data_service = MarketDataService(market_data_provider)
    registry.register("market_data", MarketContextProvider(market_data_service))
    registry.register("mock_news", NewsContextProvider())
    registry.register("mock_portfolio", PortfolioContextProvider())
    registry.register("mock_macro", MacroContextProvider())
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
