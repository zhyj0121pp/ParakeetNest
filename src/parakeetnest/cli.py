"""Local command-line entry points for ParakeetNest."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from parakeetnest.committee.agents import (
    BearAnalystAgent,
    BullAnalystAgent,
    ChairpersonAgent,
    RiskManagerAgent,
)
from parakeetnest.committee.orchestrator import CommitteeMeetingOrchestrator
from parakeetnest.committee.runtime import AgentRuntime, PromptRenderer
from parakeetnest.config import get_settings
from parakeetnest.database import (
    CommitteeMeetingRepository,
    create_session_factory,
    create_sqlite_engine,
    initialize_database,
    session_scope,
)
from parakeetnest.llm import MockLLMProvider
from parakeetnest.services import MeetingService


def build_parser() -> argparse.ArgumentParser:
    """Build the ParakeetNest CLI parser."""
    parser = argparse.ArgumentParser(prog="parakeetnest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    meeting_parser = subparsers.add_parser(
        "meeting",
        help="Run one local AI committee meeting.",
    )
    meeting_parser.add_argument("question", help="Investment question for the committee.")
    meeting_parser.add_argument(
        "--ticker",
        required=True,
        help="Ticker symbol for the committee meeting.",
    )
    meeting_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="SQLite database path. Defaults to PARAKEETNEST_SQLITE_PATH or settings.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "meeting":
        run_meeting(
            question=args.question,
            ticker=args.ticker,
            database_path=args.database,
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def run_meeting(question: str, ticker: str, database_path: Path | None = None) -> None:
    """Run one committee meeting through the application service and print the result."""
    engine = create_sqlite_engine(database_path or get_settings().sqlite_path)
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    normalized_ticker = ticker.upper()
    llm_provider = MockLLMProvider(responses=_mock_committee_responses(normalized_ticker))
    prompt_renderer = PromptRenderer()
    agent_runtime = AgentRuntime(
        llm_provider=llm_provider,
        model="mock-committee",
        prompt_renderer=prompt_renderer,
    )

    with session_scope(session_factory) as session:
        repository = CommitteeMeetingRepository(session)
        orchestrator = CommitteeMeetingOrchestrator(
            repository=repository,
            agents=(
                BullAnalystAgent(),
                BearAnalystAgent(),
                RiskManagerAgent(),
                ChairpersonAgent(),
            ),
            agent_runtime=agent_runtime,
        )
        service = MeetingService(repository=repository, orchestrator=orchestrator)
        result = service.run_meeting(question=question, ticker=normalized_ticker)

    print(f"meeting_id: {result.meeting_id}")
    print(f"status: {result.status.value}")
    print("final_result:")
    print(json.dumps(result.result_json or {}, indent=2, sort_keys=True))


def _mock_committee_responses(ticker: str) -> tuple[str, str, str, str]:
    """Return deterministic schema-valid committee responses for local CLI runs."""
    return (
        _committee_opinion(
            member_name="Bull Analyst",
            role="Chief Opportunity Hunter",
            ticker=ticker,
            viewpoint=f"{ticker} may deserve attention if catalysts improve.",
        ),
        _committee_opinion(
            member_name="Bear Analyst",
            role="Chief Fundamental Analyst",
            ticker=ticker,
            viewpoint=f"{ticker} needs stronger evidence before adding capital.",
        ),
        _committee_opinion(
            member_name="Risk Manager",
            role="Chief Risk Officer",
            ticker=ticker,
            viewpoint=f"{ticker} should be sized cautiously until risk is clearer.",
        ),
        json.dumps(
            {
                "symbol": ticker,
                "action": "watch",
                "confidence": "medium",
                "horizon": "3_months",
                "rationale": "Mock committee recommends watching while gathering real data.",
                "evidence": [
                    {
                        "summary": "Local mock committee completed all required roles.",
                        "source": "MockLLMProvider",
                    }
                ],
                "risks": ["No real market data, news, or filings were used."],
                "catalysts": ["Connect real data and LLM providers in a future epic."],
                "data_confidence": "medium",
            },
            sort_keys=True,
        ),
    )


def _committee_opinion(member_name: str, role: str, ticker: str, viewpoint: str) -> str:
    return json.dumps(
        {
            "member_name": member_name,
            "role": role,
            "symbol": ticker,
            "viewpoint": viewpoint,
            "confidence": "medium",
            "evidence": [
                {
                    "summary": "Deterministic mock response for local CLI verification.",
                    "source": "MockLLMProvider",
                }
            ],
            "risks": ["Mock output is not investment advice."],
            "catalysts": ["Replace mock provider with real research inputs later."],
        },
        sort_keys=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
