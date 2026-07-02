"""Local command-line entry points for ParakeetNest."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from parakeetnest.config import AppConfig
from parakeetnest.context import ContextRequest, MeetingContextPromptRenderer
from parakeetnest.cli import doctor


def create_app(config: AppConfig | None = None):
    """Lazily create the application container for the meeting CLI."""
    from parakeetnest.app import create_app as create_parakeetnest_app

    return create_parakeetnest_app(config)


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

    watchlist_parser = subparsers.add_parser(
        "watchlist",
        help="Review watchlist research context.",
    )
    watchlist_subparsers = watchlist_parser.add_subparsers(
        dest="watchlist_command",
        required=True,
    )
    watchlist_review_parser = watchlist_subparsers.add_parser(
        "review",
        help="Render current watchlist context without committee reasoning.",
    )
    watchlist_review_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="SQLite database path. Defaults to PARAKEETNEST_SQLITE_PATH or settings.",
    )
    watchlist_review_parser.add_argument(
        "--watchlist-seed",
        type=Path,
        default=None,
        help="Local JSON seed file for watchlist review items.",
    )

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Validate provider configuration without external API calls.",
    )
    doctor_parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional TOML integration config. Defaults to mock AppConfig.",
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

    if args.command == "watchlist" and args.watchlist_command == "review":
        run_watchlist_review(
            database_path=args.database,
            watchlist_seed_path=args.watchlist_seed,
        )
        return 0

    if args.command == "doctor":
        doctor_args = []
        if args.config is not None:
            doctor_args.extend(["--config", str(args.config)])
        return doctor.main(doctor_args)

    parser.error(f"Unknown command: {args.command}")
    return 2


def run_meeting(question: str, ticker: str, database_path: Path | None = None) -> None:
    """Run one committee meeting through the application service and print the result."""
    normalized_ticker = ticker.upper()
    config = AppConfig(database_path=database_path) if database_path is not None else None
    app = create_app(config)
    try:
        result = app.meeting_service.run(
            question=question,
            ticker=normalized_ticker,
        )
        app.commit()
    except Exception:
        app.rollback()
        raise
    finally:
        app.close()

    print(f"meeting_id: {result.meeting_id}")
    print(f"status: {result.status.value}")
    print("final_result:")
    print(json.dumps(result.result_json or {}, indent=2, sort_keys=True))


def run_watchlist_review(
    database_path: Path | None = None,
    watchlist_seed_path: Path | None = None,
) -> None:
    """Render current watchlist context without LLM or committee execution."""
    config = AppConfig(
        database_path=database_path,
        watchlist_seed_path=watchlist_seed_path,
        enabled_context_provider_ids=("watchlist",),
    )
    app = create_app(config)
    try:
        context = app.context_service.build_context(
            ContextRequest(
                question="Review watchlist context.",
                symbols=(),
                as_of=datetime.now(UTC),
                include_portfolio=False,
                include_macro=False,
                include_knowledge_base=False,
            )
        )
    finally:
        app.close()

    print(MeetingContextPromptRenderer().render(context))


if __name__ == "__main__":
    raise SystemExit(main())
