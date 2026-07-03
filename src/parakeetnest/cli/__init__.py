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
from parakeetnest.cli import daily_report
from parakeetnest.cli import schedule


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

    daily_report_parser = subparsers.add_parser(
        "daily-report",
        help="Generate a local advisory daily investment report.",
    )
    _copy_parser_arguments(
        source=daily_report.build_parser(prog="parakeetnest daily-report"),
        target=daily_report_parser,
    )

    schedule_parser = subparsers.add_parser(
        "schedule",
        help="Manage local macOS launchd scheduling.",
    )
    schedule_subparsers = schedule_parser.add_subparsers(
        dest="schedule_command",
        required=True,
    )
    schedule_install_parser = schedule_subparsers.add_parser(
        "install",
        help="Install the local macOS LaunchAgent.",
    )
    schedule._add_common_schedule_args(schedule_install_parser)
    schedule_uninstall_parser = schedule_subparsers.add_parser(
        "uninstall",
        help="Unload and remove the local macOS LaunchAgent.",
    )
    schedule._add_label_arg(schedule_uninstall_parser)
    schedule_status_parser = schedule_subparsers.add_parser(
        "status",
        help="Show launchd status for the local LaunchAgent.",
    )
    schedule._add_label_arg(schedule_status_parser)
    schedule_print_parser = schedule_subparsers.add_parser(
        "print-plist",
        help="Print the generated LaunchAgent plist.",
    )
    schedule._add_common_schedule_args(schedule_print_parser)

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

    if args.command == "daily-report":
        return daily_report.main(_daily_report_args(args))

    if args.command == "schedule":
        return schedule.run(args, parser)

    parser.error(f"Unknown command: {args.command}")
    return 2


def _copy_parser_arguments(
    *,
    source: argparse.ArgumentParser,
    target: argparse.ArgumentParser,
) -> None:
    """Copy optional CLI flags from a leaf parser into the root parser."""
    for action in source._actions:  # noqa: SLF001 - argparse has no public copier.
        if not action.option_strings:
            continue
        if isinstance(action, argparse._HelpAction):  # noqa: SLF001
            continue
        kwargs = {
            "default": action.default,
            "help": action.help,
            "required": action.required,
        }
        if isinstance(action, argparse._StoreTrueAction):  # noqa: SLF001
            kwargs["action"] = "store_true"
        elif isinstance(action, argparse._StoreFalseAction):  # noqa: SLF001
            kwargs["action"] = "store_false"
        else:
            kwargs["type"] = action.type
            kwargs["nargs"] = action.nargs
            kwargs["choices"] = action.choices
            kwargs["metavar"] = action.metavar
        target.add_argument(*action.option_strings, **kwargs)


def _daily_report_args(args: argparse.Namespace) -> list[str]:
    """Convert parsed root CLI args into the existing daily report argv."""
    forwarded: list[str] = ["--mode", args.mode]
    if args.tickers is not None:
        forwarded.append("--tickers")
        forwarded.extend(args.tickers)
    if args.output is not None:
        forwarded.extend(["--output", str(args.output)])
    if args.archive:
        forwarded.append("--archive")
    if args.account_id is not None:
        forwarded.extend(["--account-id", args.account_id])
    if args.database is not None:
        forwarded.extend(["--database", str(args.database)])
    if args.watchlist_seed is not None:
        forwarded.extend(["--watchlist-seed", str(args.watchlist_seed)])
    if args.as_of_date is not None:
        forwarded.extend(["--as-of-date", args.as_of_date.isoformat()])
    if args.email is not None:
        forwarded.extend(["--email", args.email])
    return forwarded


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
