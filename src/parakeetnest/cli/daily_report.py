"""Local CLI for generating a daily investment report file."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from parakeetnest.app import create_app
from parakeetnest.config import AppConfig, get_settings
from parakeetnest.research import DailyInvestmentReportComposer, ReportMode
from parakeetnest.research.service import InvestmentResearchService


DEFAULT_OUTPUT_PATH = Path("reports/daily-report.md")


def build_parser() -> argparse.ArgumentParser:
    """Build the daily report CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m parakeetnest.cli.daily_report",
        description="Generate a local advisory daily investment report.",
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
        default=DEFAULT_OUTPUT_PATH,
        help="Output Markdown path. Defaults to reports/daily-report.md.",
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Generate the daily investment report and write it to disk."""
    parser = build_parser()
    args = parser.parse_args(argv)
    report_mode = ReportMode.from_value(args.mode)
    explicit_tickers = _normalize_tickers(args.tickers or ())
    if args.tickers is not None and not explicit_tickers:
        parser.error("at least one ticker is required")
    app = create_app(_build_app_config(args.database, args.watchlist_seed))
    try:
        composer = _build_daily_report_composer(app)
        tickers = explicit_tickers or _watchlist_tickers(
            app.watchlist_intelligence_service
        )
        if not tickers:
            parser.error("No tickers provided and no watchlist seed is configured.")
        output_path = write_daily_report(
            tickers,
            output_path=args.output,
            account_id=args.account_id,
            as_of_date=args.as_of_date,
            mode=report_mode,
            composer=composer,
        )
    except ValueError as exc:
        parser.error(str(exc))
    finally:
        app.close()

    print(output_path)
    return 0


def write_daily_report(
    tickers: tuple[str, ...],
    *,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    account_id: str | None = None,
    as_of_date: date | None = None,
    mode: ReportMode | str = ReportMode.MORNING,
    composer: DailyInvestmentReportComposer | None = None,
) -> Path:
    """Generate a daily report body and write it to a local file."""
    report_composer = composer or DailyInvestmentReportComposer()
    body = report_composer.compose(
        tickers,
        account_id=account_id,
        as_of_date=as_of_date,
        mode=mode,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    return output_path


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
            watchlist_service=getattr(app, "watchlist_intelligence_service", None),
            intelligence_service=getattr(
                app,
                "investment_intelligence_context_service",
                None,
            ),
        )
    )


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
