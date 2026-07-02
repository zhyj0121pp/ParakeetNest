"""Local CLI runner for portfolio committee meetings."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from parakeetnest.committee.memory import (
    CommitteeMemoryService,
    SQLiteCommitteeMemoryRepository,
)
from parakeetnest.committee.models import AgentResult
from parakeetnest.committee.runtime import AgentRuntime, PromptRenderer
from parakeetnest.config import AppConfig
from parakeetnest.database import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from parakeetnest.context.providers import PortfolioContextProvider
from parakeetnest.llm import MockLLMProvider
from parakeetnest.portfolio import (
    MockPortfolioProvider,
    PortfolioService,
)
from parakeetnest.portfolio.orchestrator import (
    PortfolioCommitteeOrchestrator,
    PortfolioCommitteeResult,
)


ADVISORY_DISCLAIMER = (
    "Advisory research only. This run does not connect to brokerages, place "
    "orders, execute trades, or perform automatic rebalancing."
)


@dataclass
class PortfolioCommitteeRunner:
    """Own resources for one local portfolio committee CLI run."""

    orchestrator: PortfolioCommitteeOrchestrator
    session: Session | None = None

    def close(self) -> None:
        """Close optional persistence resources."""
        if self.session is not None:
            self.session.close()


def build_parser() -> argparse.ArgumentParser:
    """Build the portfolio committee CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m parakeetnest.cli.portfolio_committee",
        description="Run a local advisory portfolio committee meeting.",
    )
    parser.add_argument(
        "--account-id",
        default="mock-main",
        help="Mock portfolio account id to review. Defaults to mock-main.",
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable committee memory for this local run.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print additional metadata for local debugging.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="SQLite database path for committee memory.",
    )
    return parser


def create_portfolio_committee_runner(
    *,
    account_id: str,
    use_memory: bool = True,
    database_path: Path | None = None,
) -> PortfolioCommitteeRunner:
    """Wire the local portfolio committee using mock portfolio inputs."""
    portfolio_provider = MockPortfolioProvider()
    portfolio_service = PortfolioService(portfolio_provider)
    portfolio_context_provider = PortfolioContextProvider(
        portfolio_provider,
        account_id,
    )

    session: Session | None = None
    memory_service: CommitteeMemoryService | None = None
    if use_memory:
        config = AppConfig(database_path=database_path)
        engine = create_database_engine(config.resolved_database_url())
        initialize_database(engine)
        session_factory = create_session_factory(engine)
        session = session_factory()
        memory_service = CommitteeMemoryService(SQLiteCommitteeMemoryRepository(session))

    prompt_renderer = PromptRenderer()
    agent_runtime = AgentRuntime(
        llm_provider=MockLLMProvider(),
        model="mock-committee",
        prompt_renderer=prompt_renderer,
        memory_service=memory_service,
    )
    orchestrator = PortfolioCommitteeOrchestrator(
        agent_runtime=agent_runtime,
        portfolio_context_provider=portfolio_context_provider,
        memory_service=memory_service,
    )
    return PortfolioCommitteeRunner(orchestrator=orchestrator, session=session)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local portfolio committee CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    runner = create_portfolio_committee_runner(
        account_id=args.account_id,
        use_memory=not args.no_memory,
        database_path=args.database,
    )
    try:
        result = runner.orchestrator.run(
            question=f"Review portfolio account {args.account_id}.",
            ticker="PORTFOLIO",
        )
    finally:
        runner.close()

    print_portfolio_committee_result(
        result,
        account_id=args.account_id,
        memory_enabled=not args.no_memory,
        verbose=args.verbose,
    )
    return 0


def print_portfolio_committee_result(
    result: PortfolioCommitteeResult,
    *,
    account_id: str,
    memory_enabled: bool,
    verbose: bool = False,
) -> None:
    """Print a human-readable portfolio committee result."""
    print("Portfolio Committee Meeting")
    print(f"account_id: {account_id}")
    print(f"status: {result.status.value}")
    print(f"memory_enabled: {str(memory_enabled).lower()}")
    print(f"committee: {result.metadata.get('committee', 'portfolio')}")
    print(f"mode: {result.metadata.get('mode', 'advisory_analytical')}")
    print()

    portfolio = result.portfolio_context.portfolio
    if portfolio is not None:
        print("Portfolio Metadata")
        print(f"total_equity: {portfolio.total_equity}")
        print(f"cash_balance: {portfolio.cash_balance}")
        print(f"holding_count: {portfolio.holding_count}")
        print(f"symbols: {', '.join(portfolio.symbols)}")
        print()

    print("Agent Responses")
    for agent_result in result.agent_results:
        print(f"- {agent_result.agent_name} ({agent_result.agent_id})")
        payload = _agent_payload(agent_result)
        if payload:
            _print_payload_summary(payload)
        else:
            print(f"  response: {agent_result.content}")

    summary = _final_summary(result.agent_results)
    if summary is not None:
        print()
        print("Final Summary")
        print(summary)

    print()
    print("Disclaimer")
    print(ADVISORY_DISCLAIMER)

    if verbose:
        print()
        print("Metadata")
        print(json.dumps(result.metadata, indent=2, sort_keys=True))


def _agent_payload(agent_result: AgentResult) -> dict[str, Any]:
    try:
        payload = json.loads(agent_result.content)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _print_payload_summary(payload: dict[str, Any]) -> None:
    fields = (
        ("portfolio_view", "portfolio_view"),
        ("advisory_action", "action"),
        ("confidence", "confidence"),
        ("horizon", "horizon"),
    )
    for source_key, label in fields:
        value = payload.get(source_key)
        if value:
            print(f"  {label}: {value}")
    for label in ("evidence", "risks", "catalysts"):
        value = payload.get(label)
        if value:
            print(f"  {label}: {json.dumps(value, sort_keys=True)}")


def _final_summary(agent_results: tuple[AgentResult, ...]) -> str | None:
    for agent_result in reversed(agent_results):
        payload = _agent_payload(agent_result)
        for key in ("final_summary", "summary"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


if __name__ == "__main__":
    raise SystemExit(main())
