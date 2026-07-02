"""Local CLI for generating a daily investment report."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
from io import StringIO
from pathlib import Path
import sys

from parakeetnest.app import create_app
from parakeetnest.config import AppConfig, get_settings
from parakeetnest.email import ConsoleEmailProvider, EmailService
from parakeetnest.reports import (
    DailyReportOrchestrator,
    DailyReportRequest,
)
from parakeetnest.research import DailyInvestmentReportComposer, ReportMode
from parakeetnest.research.service import InvestmentResearchService


def build_parser(
    *,
    prog: str = "python -m parakeetnest.cli.daily_report",
    description: str = "Generate a local advisory daily investment report.",
) -> argparse.ArgumentParser:
    """Build the daily report CLI parser."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
    )
    parser.add_argument(
        "--mode",
        choices=tuple(mode.value for mode in ReportMode),
        default=ReportMode.MORNING.value,
        help="Report mode. Defaults to morning.",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Ticker symbols to include in the report, for example NVDA TSLA AAPL.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional Markdown path to also write the generated report.",
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Also write the generated report to the local daily archive.",
    )
    parser.add_argument(
        "--account-id",
        default=None,
        help="Optional account id for portfolio context.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="SQLite database path. Defaults to PARAKEETNEST_SQLITE_PATH or settings.",
    )
    parser.add_argument(
        "--watchlist-seed",
        type=Path,
        default=None,
        help="Local JSON seed file for default daily report tickers.",
    )
    parser.add_argument(
        "--as-of-date",
        type=_parse_date,
        default=None,
        help="Optional report date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Optional email recipient for console email delivery.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Generate the daily investment report and print it to stdout."""
    parser = build_parser()
    args = parser.parse_args(argv)
    app = create_app(_build_app_config(args.database, args.watchlist_seed))
    email_output = StringIO()
    try:
        request = build_daily_report_request(args, app, parser)
        orchestrator = build_daily_report_orchestrator(args, app, email_output)
        result = orchestrator.run(request)
    except ValueError as exc:
        parser.error(str(exc))
    except Exception as exc:
        print(f"daily report generation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        app.close()

    print(result.body, end="" if result.body.endswith("\n") else "\n")
    if args.email:
        print(email_output.getvalue(), end="")
    return 0


def build_daily_report_request(
    args: argparse.Namespace,
    app: object,
    parser: argparse.ArgumentParser,
) -> DailyReportRequest:
    """Build a daily report request from parsed CLI arguments."""
    report_mode = ReportMode.from_value(args.mode)
    explicit_tickers = _normalize_tickers(args.tickers or ())
    if args.tickers is not None and not explicit_tickers:
        parser.error("at least one ticker is required")
    tickers = explicit_tickers or _watchlist_tickers(app.watchlist_intelligence_service)
    if not tickers:
        parser.error("No tickers provided and no watchlist seed is configured.")
    return DailyReportRequest(
        mode=report_mode,
        tickers=tickers,
        account_id=args.account_id,
        as_of_date=args.as_of_date,
        archive=args.archive,
        output_path=args.output,
        email_recipient=args.email,
    )


def build_daily_report_orchestrator(
    args: argparse.Namespace,
    app: object,
    email_output: StringIO,
) -> DailyReportOrchestrator:
    """Build the daily report orchestrator from parsed CLI arguments."""
    return DailyReportOrchestrator(
        composer=_build_daily_report_composer(app),
        email_service=(
            EmailService(ConsoleEmailProvider(stream=email_output))
            if args.email
            else None
        ),
    )


def _build_app_config(
    database_path: Path | None,
    watchlist_seed_path: Path | None,
) -> AppConfig:
    settings = get_settings()
    return AppConfig(
        database_path=database_path,
        watchlist_seed_path=watchlist_seed_path or settings.watchlist_seed_path,
    )


def _build_daily_report_composer(app: object) -> DailyInvestmentReportComposer:
    """Build the report composer from existing application services."""
    return DailyInvestmentReportComposer(
        research_service=InvestmentResearchService(
            portfolio_context_provider=_context_provider(app, "portfolio"),
            watchlist_service=getattr(app, "watchlist_intelligence_service", None),
            intelligence_service=getattr(
                app,
                "investment_intelligence_context_service",
                None,
            ),
        )
    )


def _context_provider(app: object, provider_id: str) -> object | None:
    registry = getattr(app, "context_provider_registry", None)
    if registry is None or not hasattr(registry, "list_registrations"):
        return None
    for registration in registry.list_registrations():
        if registration.provider_id == provider_id and registration.enabled:
            return registration.provider
    return None


def _watchlist_tickers(watchlist_service: object | None) -> tuple[str, ...]:
    if watchlist_service is None or not hasattr(watchlist_service, "build_all_insights"):
        return ()
    return tuple(
        insight.symbol
        for insight in watchlist_service.build_all_insights()
        if getattr(insight, "symbol", None)
    )


def _normalize_tickers(tickers: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for ticker in tickers:
        symbol = ticker.strip().upper()
        if symbol:
            normalized.append(symbol)
    return tuple(normalized)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "as-of-date must use YYYY-MM-DD format"
        ) from exc


if __name__ == "__main__":
    raise SystemExit(main())
