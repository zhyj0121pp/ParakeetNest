"""Tests for the daily report CLI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from parakeetnest.cli import daily_report
from parakeetnest.research import ReportMode


class RecordingComposer:
    def __init__(self, body: str = "daily report body\n") -> None:
        self.body = body
        self.calls: list[dict[str, object]] = []

    def compose(
        self,
        tickers: tuple[str, ...],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
    ) -> str:
        self.calls.append(
            {
                "tickers": tickers,
                "account_id": account_id,
                "as_of_date": as_of_date,
                "mode": mode,
            }
        )
        return self.body


class EmptyWatchlistService:
    def build_all_insights(self) -> tuple[object, ...]:
        return ()

    def build_insight(self, symbol: str) -> object:
        raise ValueError(f"missing {symbol}")


@dataclass(frozen=True)
class FakeContextProviderRegistration:
    provider_id: str
    provider: object
    enabled: bool = True


class FakeContextProviderRegistry:
    def __init__(
        self,
        registrations: tuple[FakeContextProviderRegistration, ...],
    ) -> None:
        self._registrations = registrations

    def list_registrations(self) -> tuple[FakeContextProviderRegistration, ...]:
        return self._registrations


class RecordingApp:
    def __init__(
        self,
        watchlist_service: object | None = None,
        intelligence_service: object | None = None,
        portfolio_context_provider: object | None = None,
    ) -> None:
        self.watchlist_intelligence_service = (
            watchlist_service or EmptyWatchlistService()
        )
        self.investment_intelligence_context_service = intelligence_service
        registrations = ()
        if portfolio_context_provider is not None:
            registrations = (
                FakeContextProviderRegistration(
                    provider_id="portfolio",
                    provider=portfolio_context_provider,
                ),
            )
        self.context_provider_registry = FakeContextProviderRegistry(registrations)
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def recording_app(monkeypatch: pytest.MonkeyPatch) -> RecordingApp:
    app = RecordingApp()
    monkeypatch.setattr(daily_report, "create_app", lambda config: app)
    return app


def test_cli_writes_report_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer("Market Summary\nCommittee Consensus\n")
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )
    output_path = tmp_path / "daily-report.md"

    exit_code = daily_report.main(["--tickers", "NVDA", "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == (
        "Market Summary\nCommittee Consensus\n"
    )
    assert recording_app.closed is True
    assert capsys.readouterr().out == "Market Summary\nCommittee Consensus\n"


def test_cli_prints_report_to_stdout_without_default_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    exit_code = daily_report.main(["--tickers", "NVDA"])

    assert exit_code == 0
    assert not (tmp_path / "reports" / "daily-report.md").exists()
    assert capsys.readouterr().out == "daily report body\n"
    assert composer.calls[0]["mode"] is ReportMode.MORNING


def test_cli_invokes_email_service_when_email_is_specified(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer("Market Summary\n")
    sent: list[dict[str, object]] = []

    class RecordingEmailService:
        def __init__(self, provider: object) -> None:
            self.provider = provider

        def send(
            self,
            report: str,
            *,
            recipient: str,
            as_of_date: date | None = None,
            mode: ReportMode | str | None = None,
        ) -> None:
            sent.append(
                {
                    "report": report,
                    "recipient": recipient,
                    "as_of_date": as_of_date,
                    "mode": mode,
                }
            )

    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )
    monkeypatch.setattr(daily_report, "EmailService", RecordingEmailService)

    exit_code = daily_report.main(
        [
            "--tickers",
            "NVDA",
            "--as-of-date",
            "2026-07-01",
            "--email",
            "investor@example.com",
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out == "Market Summary\n"
    assert sent == [
        {
            "report": "Market Summary\n",
            "recipient": "investor@example.com",
            "as_of_date": date(2026, 7, 1),
            "mode": ReportMode.MORNING,
        }
    ]


def test_cli_prints_report_and_real_console_email_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer("Market Summary\nCommittee Consensus\n")
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    exit_code = daily_report.main(
        [
            "--mode",
            "evening",
            "--tickers",
            "NVDA",
            "--as-of-date",
            "2026-07-01",
            "--email",
            "investor@example.com",
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out == (
        "Market Summary\n"
        "Committee Consensus\n"
        "==== EMAIL ====\n"
        "To: investor@example.com\n"
        "Subject: Evening Investment Review - 2026-07-01\n"
        "\n"
        "Market Summary\n"
        "Committee Consensus\n"
        "\n"
        "==============\n"
    )


def test_cli_does_not_send_email_when_email_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer("Market Summary\n")
    sent: list[object] = []

    class RecordingEmailService:
        def __init__(self, provider: object) -> None:
            self.provider = provider

        def send(self, *args: object, **kwargs: object) -> None:
            sent.append((args, kwargs))

    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )
    monkeypatch.setattr(daily_report, "EmailService", RecordingEmailService)

    exit_code = daily_report.main(["--tickers", "NVDA"])

    assert exit_code == 0
    assert capsys.readouterr().out == "Market Summary\n"
    assert sent == []


def test_cli_dispatches_morning_mode(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer()
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    exit_code = daily_report.main(["--mode", "morning", "--tickers", "NVDA"])

    assert exit_code == 0
    assert capsys.readouterr().out == "daily report body\n"
    assert composer.calls[0]["mode"] is ReportMode.MORNING


def test_cli_dispatches_evening_mode(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer()
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    exit_code = daily_report.main(["--mode", "evening", "--tickers", "NVDA"])

    assert exit_code == 0
    assert capsys.readouterr().out == "daily report body\n"
    assert composer.calls[0]["mode"] is ReportMode.EVENING


def test_invalid_mode_returns_clear_error(
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    with pytest.raises(SystemExit) as exc:
        daily_report.main(["--mode", "midday", "--tickers", "NVDA"])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "invalid choice: 'midday'" in captured.err


def test_custom_output_path_works(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer()
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )
    output_path = tmp_path / "nested" / "custom.md"

    exit_code = daily_report.main(
        ["--tickers", "TSLA", "--output", str(output_path)]
    )

    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == "daily report body\n"


def test_morning_archive_path_uses_report_date(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    exit_code = daily_report.main(
        [
            "--mode",
            "morning",
            "--tickers",
            "NVDA",
            "--as-of-date",
            "2026-07-01",
            "--archive",
        ]
    )

    archive_path = (
        tmp_path
        / "reports"
        / "2026-07-01"
        / "morning-investment-brief.md"
    )
    assert exit_code == 0
    assert archive_path.read_text(encoding="utf-8") == "daily report body\n"


def test_evening_archive_path_uses_report_date(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    exit_code = daily_report.main(
        [
            "--mode",
            "evening",
            "--tickers",
            "NVDA",
            "--as-of-date",
            "2026-07-01",
            "--archive",
        ]
    )

    archive_path = (
        tmp_path
        / "reports"
        / "2026-07-01"
        / "evening-investment-review.md"
    )
    assert exit_code == 0
    assert archive_path.read_text(encoding="utf-8") == "daily report body\n"


def test_archive_and_output_together_write_both_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )
    output_path = tmp_path / "custom" / "daily-report.md"

    exit_code = daily_report.main(
        [
            "--mode",
            "morning",
            "--tickers",
            "NVDA",
            "--as-of-date",
            "2026-07-01",
            "--archive",
            "--output",
            str(output_path),
        ]
    )

    archive_path = (
        tmp_path
        / "reports"
        / "2026-07-01"
        / "morning-investment-brief.md"
    )
    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == "daily report body\n"
    assert archive_path.read_text(encoding="utf-8") == "daily report body\n"


def test_ticker_arguments_are_passed_through(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer()
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )
    output_path = tmp_path / "daily-report.md"

    exit_code = daily_report.main(
        [
            "--tickers",
            "nvda",
            "TSLA",
            " aapl ",
            "--account-id",
            "main",
            "--as-of-date",
            "2026-07-01",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert composer.calls == [
        {
            "tickers": ("NVDA", "TSLA", "AAPL"),
            "account_id": "main",
            "as_of_date": date(2026, 7, 1),
            "mode": ReportMode.MORNING,
        }
    ]


def test_cli_runs_without_tickers_when_watchlist_seed_exists(tmp_path: Path) -> None:
    seed_path = tmp_path / "watchlist.json"
    seed_path.write_text(
        """
        [
          {
            "symbol": "NVDA",
            "theme": "AI infrastructure",
            "reason": "Track AI accelerator demand",
            "priority": "high"
          }
        ]
        """,
        encoding="utf-8",
    )
    output_path = tmp_path / "daily-report.md"

    exit_code = daily_report.main(
        [
            "--database",
            str(tmp_path / "daily.sqlite3"),
            "--watchlist-seed",
            str(seed_path),
            "--output",
            str(output_path),
        ]
    )

    body = output_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Morning Investment Brief" in body
    assert "Report Mode: morning" in body
    assert "Tickers: NVDA" in body
    assert "Factual Ticker Context" in body
    assert "Track AI accelerator demand. Theme: AI infrastructure." in body
    assert "Watchlist Focus" in body
    assert "Watchlist review found 1 covered watchlist item(s)." in body
    assert "No watchlist service connected." not in body


def test_cli_explicit_tickers_override_watchlist_seed(tmp_path: Path) -> None:
    seed_path = tmp_path / "watchlist.json"
    seed_path.write_text(
        """
        [
          {
            "symbol": "NVDA",
            "reason": "Track AI accelerator demand"
          }
        ]
        """,
        encoding="utf-8",
    )
    output_path = tmp_path / "daily-report.md"

    exit_code = daily_report.main(
        [
            "--tickers",
            "TSLA",
            "--database",
            str(tmp_path / "daily.sqlite3"),
            "--watchlist-seed",
            str(seed_path),
            "--output",
            str(output_path),
        ]
    )

    body = output_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Tickers: TSLA" in body
    assert "Tickers: NVDA" not in body
    assert "TSLA is included for research" in body


def test_cli_evening_mode_renders_evening_report(tmp_path: Path) -> None:
    output_path = tmp_path / "evening-review.md"

    exit_code = daily_report.main(
        [
            "--mode",
            "evening",
            "--tickers",
            "NVDA",
            "--database",
            str(tmp_path / "daily.sqlite3"),
            "--output",
            str(output_path),
        ]
    )

    body = output_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Evening Investment Review" in body
    assert "Report Mode: evening" in body
    assert "What Changed" in body
    assert "Tomorrow’s Focus" in body


def test_generation_failure_returns_nonzero_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    class FailingComposer:
        def compose(self, *args: object, **kwargs: object) -> str:
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: FailingComposer(),
    )

    exit_code = daily_report.main(["--mode", "morning", "--tickers", "NVDA"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "daily report generation failed: provider unavailable" in captured.err


def test_watchlist_service_is_passed_into_daily_report_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watchlist_service = EmptyWatchlistService()
    app = RecordingApp(watchlist_service=watchlist_service)
    received: list[object] = []

    class RecordingResearchService:
        def __init__(self, **kwargs: object) -> None:
            received.append(kwargs["watchlist_service"])

        def generate_report(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("report generation is not needed")

    monkeypatch.setattr(
        daily_report,
        "InvestmentResearchService",
        RecordingResearchService,
    )

    composer = daily_report._build_daily_report_composer(app)

    assert composer is not None
    assert received == [watchlist_service]


def test_portfolio_context_provider_is_passed_into_daily_report_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portfolio_context_provider = object()
    app = RecordingApp(portfolio_context_provider=portfolio_context_provider)
    received: list[object] = []

    class RecordingResearchService:
        def __init__(self, **kwargs: object) -> None:
            received.append(kwargs["portfolio_context_provider"])

        def generate_report(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("report generation is not needed")

    monkeypatch.setattr(
        daily_report,
        "InvestmentResearchService",
        RecordingResearchService,
    )

    composer = daily_report._build_daily_report_composer(app)

    assert composer is not None
    assert received == [portfolio_context_provider]


def test_report_includes_committee_opinion_sections(tmp_path: Path) -> None:
    output_path = tmp_path / "daily-report.md"

    exit_code = daily_report.main(
        [
            "--tickers",
            "NVDA",
            "--database",
            str(tmp_path / "daily.sqlite3"),
            "--output",
            str(output_path),
        ]
    )

    body = output_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Market Setup" in body
    assert "Portfolio Watch" in body
    assert "Watchlist Focus" in body
    assert "Today’s Focus" in body
    assert "Dongdong’s Opportunity View" in body
    assert "Xixi’s Fundamental View" in body
    assert "Youyou’s Risk View" in body
    assert "Committee Consensus" in body
    assert "Confidence" in body
    assert "Key Risks" in body
    assert "Upcoming Catalysts" in body
    assert "Today's Suggested Actions" in body
    assert "Recommendations" not in body


def test_missing_tickers_without_watchlist_seed_return_clear_error(
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    with pytest.raises(SystemExit) as exc:
        daily_report.main([])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "No tickers provided and no watchlist seed is configured." in captured.err


def test_invalid_tickers_return_clear_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        daily_report.main(["--tickers", "   "])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "at least one ticker is required" in captured.err


def test_daily_report_cli_adds_no_broker_trading_or_llm_provider_logic() -> None:
    source = Path(daily_report.__file__).read_text(encoding="utf-8").lower()

    forbidden_terms = (
        "broker",
        "brokerage",
        "place_order",
        "execute_trade",
        "automatic_trading",
        "rebalance_account",
        "openai",
        "llmprovider",
    )
    for term in forbidden_terms:
        assert term not in source
