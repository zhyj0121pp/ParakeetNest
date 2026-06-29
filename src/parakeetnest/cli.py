"""Local command-line entry points for ParakeetNest."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from parakeetnest.app import create_app
from parakeetnest.config import AppConfig


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
    normalized_ticker = ticker.upper()
    config = AppConfig(database_path=database_path) if database_path is not None else None
    app = create_app(config)
    try:
        result = app.meeting_service.run_meeting(
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


if __name__ == "__main__":
    raise SystemExit(main())
