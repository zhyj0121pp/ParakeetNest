"""Local CLI for generating a daily investment report."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path
import sys

from parakeetnest.app import create_app
from parakeetnest.config import (
    AppConfig,
    default_portfolio_account_id,
    email_config_from_settings,
    get_settings,
    portfolio_config_from_settings,
)
from parakeetnest.email import EmailReportDeliveryProvider
from parakeetnest.reports import (
    DailyReportOrchestrator,
    DailyReportRequest,
)
from parakeetnest.research import (
    DailyInvestmentReportComposer,
    ReportDeliveryService,
    ReportMode,
    inspect_committee_fact_inputs,
)
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
        help="Optional HTML path to also write the generated report.",
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
    parser.add_argument(
        "--inspect-context",
        action="store_true",
        help=(
            "Print ticker-level committee fact inputs instead of rendering the "
            "HTML report."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Generate the daily investment report and print it to stdout."""
    parser = build_parser()
    args = parser.parse_args(argv)
    app = create_app(_build_app_config(args.database, args.watchlist_seed))
    try:
        request = build_daily_report_request(args, app, parser)
        if args.inspect_context:
            report = _build_daily_report_composer(app).compose_report(
                request.tickers,
                account_id=request.account_id,
                as_of_date=request.as_of_date,
                mode=request.mode,
            )
            print(inspect_committee_fact_inputs(report), end="")
            return 0
        orchestrator = build_daily_report_orchestrator(request, app)
        result = orchestrator.run(request)
    except ValueError as exc:
        parser.error(str(exc))
    except Exception as exc:
        print(f"daily report generation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        app.close()

    print(result.body, end="" if result.body.endswith("\n") else "\n")
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
    account_id = _resolve_account_id(args.account_id, app)
    tickers = (
        explicit_tickers
        or _portfolio_tickers(app, account_id)
        or _watchlist_tickers(app.watchlist_intelligence_service)
    )
    if not tickers:
        parser.error(
            "No tickers provided, no portfolio holdings found, "
            "and no watchlist seed is configured."
        )
    return DailyReportRequest(
        mode=report_mode,
        tickers=tickers,
        account_id=account_id,
        as_of_date=args.as_of_date,
        archive=args.archive,
        output_path=args.output,
        email_recipient=_resolve_email_recipient(args.email, app),
    )


def build_daily_report_orchestrator(
    request: DailyReportRequest,
    app: object,
) -> DailyReportOrchestrator:
    """Build the daily report orchestrator from parsed CLI arguments."""
    return DailyReportOrchestrator(
        composer=_build_daily_report_composer(app),
        delivery_service=(
            ReportDeliveryService(_report_delivery_provider(app))
            if request.email_recipient
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
        portfolio=portfolio_config_from_settings(settings),
        email=email_config_from_settings(settings),
        report_recipient_email=settings.report_recipient,
    )


def _build_daily_report_composer(app: object) -> DailyInvestmentReportComposer:
    """Build the report composer from existing application services."""
    config = getattr(app, "config", None)
    llm_config = getattr(config, "llm", None)
    return DailyInvestmentReportComposer(
        research_service=InvestmentResearchService(
            portfolio_service=getattr(app, "portfolio_service", None),
            portfolio_context_provider=_context_provider(app, "portfolio"),
            public_context_service=getattr(app, "context_service", None),
            watchlist_service=getattr(app, "watchlist_intelligence_service", None),
            intelligence_service=getattr(
                app,
                "investment_intelligence_context_service",
                None,
            ),
            llm_provider=getattr(app, "llm_provider", None),
            llm_model=getattr(llm_config, "model", None),
            llm_temperature=getattr(llm_config, "temperature", 0.0),
        )
    )


def _report_delivery_provider(app: object) -> object:
    provider = getattr(app, "report_delivery_provider", None)
    if provider is not None:
        return provider
    return EmailReportDeliveryProvider(app.email_provider)


def _context_provider(app: object, provider_id: str) -> object | None:
    registry = getattr(app, "context_provider_registry", None)
    if registry is None or not hasattr(registry, "list_registrations"):
        return None
    for registration in registry.list_registrations():
        if registration.provider_id == provider_id and registration.enabled:
            return registration.provider
    return None


def _resolve_account_id(explicit_account_id: str | None, app: object) -> str | None:
    if explicit_account_id is not None and explicit_account_id.strip():
        return explicit_account_id.strip()
    config = getattr(app, "config", None)
    portfolio_config = getattr(config, "portfolio", None)
    if portfolio_config is None:
        return None
    return default_portfolio_account_id(portfolio_config)


def _resolve_email_recipient(explicit_email: str | None, app: object) -> str | None:
    if explicit_email is not None and explicit_email.strip():
        return explicit_email.strip()
    config = getattr(app, "config", None)
    configured_email = getattr(config, "report_recipient_email", None)
    if configured_email is not None and configured_email.strip():
        return configured_email.strip()
    return None


def _portfolio_tickers(app: object, account_id: str | None) -> tuple[str, ...]:
    if account_id is None:
        return ()
    portfolio_service = getattr(app, "portfolio_service", None)
    if portfolio_service is None:
        return ()
    if hasattr(portfolio_service, "get_symbols"):
        return _normalize_tickers(portfolio_service.get_symbols(account_id))
    if hasattr(portfolio_service, "get_snapshot"):
        snapshot = portfolio_service.get_snapshot(account_id)
        if hasattr(snapshot, "symbols"):
            return _normalize_tickers(snapshot.symbols())
        return _normalize_tickers(
            getattr(holding, "symbol", "")
            for holding in getattr(snapshot, "holdings", ())
        )
    return ()


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
