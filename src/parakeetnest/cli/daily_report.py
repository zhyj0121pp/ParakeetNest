"""Local CLI for generating a daily investment report file."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from parakeetnest.research import DailyInvestmentReportComposer


DEFAULT_OUTPUT_PATH = Path("reports/daily-report.md")


def build_parser() -> argparse.ArgumentParser:
    """Build the daily report CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m parakeetnest.cli.daily_report",
        description="Generate a local advisory daily investment report.",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        required=True,
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
    tickers = _normalize_tickers(args.tickers)
    if not tickers:
        parser.error("at least one ticker is required")

    try:
        output_path = write_daily_report(
            tickers,
            output_path=args.output,
            account_id=args.account_id,
            as_of_date=args.as_of_date,
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(output_path)
    return 0


def write_daily_report(
    tickers: tuple[str, ...],
    *,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    account_id: str | None = None,
    as_of_date: date | None = None,
    composer: DailyInvestmentReportComposer | None = None,
) -> Path:
    """Generate a daily report body and write it to a local file."""
    report_composer = composer or DailyInvestmentReportComposer()
    body = report_composer.compose(
        tickers,
        account_id=account_id,
        as_of_date=as_of_date,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    return output_path


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
