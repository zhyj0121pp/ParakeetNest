"""Manual scheduler entry point for daily investment reports."""

from __future__ import annotations

from collections.abc import Sequence
from io import StringIO
import sys

from parakeetnest.cli import daily_report
from parakeetnest.scheduler import DailyReportScheduledJob


def main(argv: Sequence[str] | None = None) -> int:
    """Trigger one scheduler-compatible daily report job."""
    parser = daily_report.build_parser(
        prog="python -m parakeetnest.cli.scheduled_daily_report",
        description="Run one scheduled daily investment report job manually.",
    )
    args = parser.parse_args(argv)
    app = daily_report.create_app(
        daily_report._build_app_config(args.database, args.watchlist_seed)
    )
    email_output = StringIO()
    try:
        request = daily_report.build_daily_report_request(args, app, parser)
        orchestrator = daily_report.build_daily_report_orchestrator(
            args,
            app,
            email_output,
        )
        result = DailyReportScheduledJob(
            orchestrator=orchestrator,
            request=request,
        ).run()
    except ValueError as exc:
        parser.error(str(exc))
    except Exception as exc:
        print(f"scheduled daily report failed: {exc}", file=sys.stderr)
        return 1
    finally:
        app.close()

    print(result.body, end="" if result.body.endswith("\n") else "\n")
    if args.email:
        print(email_output.getvalue(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
