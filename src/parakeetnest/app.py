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
from parakeetnest.context.service import ContextService
from parakeetnest.database import (
    CommitteeMeetingRepository,
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from parakeetnest.llm import LLMProvider, MockLLMProvider
from parakeetnest.services import MeetingService


@dataclass
class ParakeetNestApp:
    """Application container for ParakeetNest services."""

    config: AppConfig
    meeting_repository: CommitteeMeetingRepository
    prompt_renderer: PromptRenderer
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
    context_service = ContextService(
        providers=(
            MarketContextProvider(),
            NewsContextProvider(),
            PortfolioContextProvider(),
            MacroContextProvider(),
            KnowledgeBaseContextProvider(),
        )
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
