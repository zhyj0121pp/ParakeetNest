"""Tests for the daily report CLI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from parakeetnest.cli import daily_report
from parakeetnest.config import get_settings
from parakeetnest.research import (
    InvestmentResearchReport,
    ReportBodyFormat,
    ReportMode,
    ResearchTickerReport,
)
from parakeetnest.research.delivery import ReportDeliveryResult


class RecordingComposer:
    def __init__(
        self,
        body: str = "legacy report body\n",
        html_body: str = "<!doctype html>\n<html><body>daily report body</body></html>\n",
    ) -> None:
        self.body = body
        self.html_body = html_body
        self.calls: list[dict[str, object]] = []

    def compose(
        self,
        tickers: tuple[str, ...],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
        body_format: ReportBodyFormat | str = (
            ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT
        ),
    ) -> str:
        self.calls.append(
            {
                "tickers": tickers,
                "account_id": account_id,
                "as_of_date": as_of_date,
                "mode": mode,
                "body_format": body_format,
            }
        )
        if body_format is ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT:
            return self.html_body
        return self.body

    def compose_report(
        self,
        tickers: tuple[str, ...],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
    ) -> InvestmentResearchReport:
        self.calls.append(
            {
                "tickers": tickers,
                "account_id": account_id,
                "as_of_date": as_of_date,
                "mode": mode,
                "body_format": "inspect_context",
            }
        )
        return InvestmentResearchReport(
            ticker_reports=(
                ResearchTickerReport(
                    ticker=tickers[0],
                    summary="diagnostic report",
                    bull_case=("No connected factual context available.",),
                    bear_case=("No connected factual context available.",),
                    risks=(),
                    catalysts=(),
                    public_market_facts=("Yahoo/market_data: NVDA price=204.12",),
                    company_facts=("SEC EDGAR: NVDA 10-Q",),
                    macro_facts=("FRED/macro: Fed Funds 3.5",),
                    source_summaries=("market_data: public market facts",),
                ),
            ),
            mode=mode,
        )


class EmptyWatchlistService:
    def build_all_insights(self) -> tuple[object, ...]:
        return ()

    def build_insight(self, symbol: str) -> object:
        raise ValueError(f"missing {symbol}")


class RecordingPortfolioService:
    def __init__(self, symbols: tuple[str, ...]) -> None:
        self.symbols = symbols
        self.calls: list[str] = []

    def get_symbols(self, account_id: str) -> tuple[str, ...]:
        self.calls.append(account_id)
        return self.symbols


@dataclass(frozen=True)
class FakePortfolioConfig:
    provider: str = "mock"
    account_id: str | None = None


@dataclass(frozen=True)
class FakeConfig:
    portfolio: FakePortfolioConfig
    report_recipient_email: str | None = None


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
        portfolio_service: object | None = None,
        portfolio_config: FakePortfolioConfig | None = None,
        email_provider: object | None = None,
        report_delivery_provider: object | None = None,
        report_recipient_email: str | None = None,
    ) -> None:
        self.config = FakeConfig(
            portfolio_config or FakePortfolioConfig(),
            report_recipient_email=report_recipient_email,
        )
        self.email_provider = email_provider or object()
        self.report_delivery_provider = report_delivery_provider
        self.portfolio_service = portfolio_service
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


class RecordingReportDeliveryProvider:
    provider_name = "recording"

    def __init__(self, result: ReportDeliveryResult | None = None) -> None:
        self.requests: list[object] = []
        self.result = result or ReportDeliveryResult.delivered(
            provider_name=self.provider_name
        )

    def deliver(self, request: object) -> ReportDeliveryResult:
        self.requests.append(request)
        return self.result


def _assert_html_attachment_delivery(
    request: object,
    *,
    recipient: str,
    report_date: str,
    html_report: str,
) -> None:
    assert request.recipient.email == recipient
    assert request.body == (
        "Morning Investment Report\n"
        f"Date: {report_date}\n"
        f"Full report is attached: morning-report-{report_date}.html"
    )
    assert request.content_type == "text/plain"
    assert request.attachments[0].filename == f"morning-report-{report_date}.html"
    assert request.attachments[0].content == html_report.strip()
    assert request.attachments[0].content_type == "text/html"


@pytest.fixture(autouse=True)
def _english_report_language(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    monkeypatch.setenv("PARAKEETNEST_EMAIL_PROVIDER", "mock")
    monkeypatch.setenv("PARAKEETNEST_LLM_PROVIDER", "mock")
    monkeypatch.setenv("PARAKEETNEST_LLM_MODEL", "mock-committee")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
    composer = RecordingComposer(
        "Market Summary\nCommittee Consensus\n",
        html_body=(
            "<!doctype html>\n"
            "<html><body>Market Summary Committee Consensus</body></html>\n"
        ),
    )
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )
    output_path = tmp_path / "daily-report.html"

    exit_code = daily_report.main(["--tickers", "NVDA", "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == (
        "<!doctype html>\n"
        "<html><body>Market Summary Committee Consensus</body></html>\n"
    )
    assert recording_app.closed is True
    assert capsys.readouterr().out == ""


def test_cli_delegates_workflow_to_daily_report_orchestrator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    captured: dict[str, object] = {}
    output_path = tmp_path / "daily-report.html"

    @dataclass(frozen=True)
    class FakeResult:
        body: str

    class RecordingOrchestrator:
        def __init__(self, **kwargs: object) -> None:
            captured["init"] = kwargs

        def run(self, request: object) -> FakeResult:
            captured["request"] = request
            return FakeResult(body="delegated body\n")

    monkeypatch.setattr(daily_report, "DailyReportOrchestrator", RecordingOrchestrator)

    exit_code = daily_report.main(
        [
            "--mode",
            "evening",
            "--tickers",
            "nvda",
            "--account-id",
            "main",
            "--as-of-date",
            "2026-07-01",
            "--archive",
            "--output",
            str(output_path),
        ]
    )

    request = captured["request"]
    assert exit_code == 0
    assert capsys.readouterr().out == ""
    assert request.mode is ReportMode.EVENING
    assert request.tickers == ("NVDA",)
    assert request.account_id == "main"
    assert request.as_of_date == date(2026, 7, 1)
    assert request.archive is True
    assert request.output_path == output_path
    assert request.email_recipient is None
    assert "composer" in captured["init"]


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
    assert not (tmp_path / "reports" / "daily-report.html").exists()
    assert capsys.readouterr().out == (
        "<!doctype html>\n<html><body>daily report body</body></html>\n"
    )
    assert composer.calls[0]["mode"] is ReportMode.MORNING


def test_cli_inspect_context_prints_ticker_fact_inputs(
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

    exit_code = daily_report.main(["--tickers", "NVDA", "--inspect-context"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "ticker: NVDA" in output
    assert "public_market_facts:" in output
    assert "Yahoo/market_data: NVDA price=204.12" in output
    assert "company_facts:" in output
    assert "SEC EDGAR: NVDA 10-Q" in output
    assert composer.calls[0]["body_format"] == "inspect_context"
    assert recording_app.closed is True


def test_cli_invokes_report_delivery_when_email_is_specified(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    delivery_provider = RecordingReportDeliveryProvider()
    recording_app.report_delivery_provider = delivery_provider
    html_report = "<!doctype html>\n<html><body>Market Summary</body></html>\n"
    composer = RecordingComposer(
        "Market Summary\n",
        html_body=html_report,
    )

    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    try:
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
    finally:
        get_settings.cache_clear()

    assert exit_code == 0
    assert capsys.readouterr().out == ""
    assert len(delivery_provider.requests) == 1
    _assert_html_attachment_delivery(
        delivery_provider.requests[0],
        recipient="investor@example.com",
        report_date="2026-07-01",
        html_report=html_report,
    )


def test_cli_sends_report_through_app_email_provider(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    delivery_provider = RecordingReportDeliveryProvider()
    recording_app.report_delivery_provider = delivery_provider
    html_report = (
        "<!doctype html>\n"
        "<html><body>Market Summary Committee Consensus</body></html>\n"
    )
    composer = RecordingComposer(
        "Market Summary\nCommittee Consensus\n",
        html_body=html_report,
    )

    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    try:
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
    finally:
        get_settings.cache_clear()

    assert exit_code == 0
    assert capsys.readouterr().out == ""
    assert len(delivery_provider.requests) == 1
    _assert_html_attachment_delivery(
        delivery_provider.requests[0],
        recipient="investor@example.com",
        report_date="2026-07-01",
        html_report=html_report,
    )


def test_cli_uses_configured_report_recipient_when_email_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    delivery_provider = RecordingReportDeliveryProvider()
    app = RecordingApp(
        report_delivery_provider=delivery_provider,
        report_recipient_email="configured@example.com",
    )
    html_report = "<!doctype html>\n<html><body>Market Summary</body></html>\n"
    composer = RecordingComposer(
        "Market Summary\n",
        html_body=html_report,
    )

    monkeypatch.setattr(daily_report, "create_app", lambda config: app)
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    try:
        exit_code = daily_report.main(
            ["--tickers", "NVDA", "--as-of-date", "2026-07-01"]
        )
    finally:
        get_settings.cache_clear()

    assert exit_code == 0
    assert capsys.readouterr().out == ""
    assert len(delivery_provider.requests) == 1
    _assert_html_attachment_delivery(
        delivery_provider.requests[0],
        recipient="configured@example.com",
        report_date="2026-07-01",
        html_report=html_report,
    )


def test_cli_email_flag_without_value_uses_configured_report_recipient(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    delivery_provider = RecordingReportDeliveryProvider()
    app = RecordingApp(
        report_delivery_provider=delivery_provider,
        report_recipient_email="configured@example.com",
    )
    html_report = "<!doctype html>\n<html><body>Market Summary</body></html>\n"
    composer = RecordingComposer(
        "Market Summary\n",
        html_body=html_report,
    )

    monkeypatch.setattr(daily_report, "create_app", lambda config: app)
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    try:
        exit_code = daily_report.main(
            ["--tickers", "NVDA", "--as-of-date", "2026-07-01", "--email"]
        )
    finally:
        get_settings.cache_clear()

    assert exit_code == 0
    assert capsys.readouterr().out == ""
    assert len(delivery_provider.requests) == 1
    _assert_html_attachment_delivery(
        delivery_provider.requests[0],
        recipient="configured@example.com",
        report_date="2026-07-01",
        html_report=html_report,
    )


def test_cli_returns_nonzero_when_email_delivery_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    delivery_provider = RecordingReportDeliveryProvider(
        ReportDeliveryResult.failed(
            provider_name="recording",
            error_message="token expired",
        )
    )
    app = RecordingApp(
        report_delivery_provider=delivery_provider,
        report_recipient_email="configured@example.com",
    )
    html_report = "<!doctype html>\n<html><body>Market Summary</body></html>\n"
    composer = RecordingComposer(
        "Market Summary\n",
        html_body=html_report,
    )

    monkeypatch.setattr(daily_report, "create_app", lambda config: app)
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    try:
        exit_code = daily_report.main(
            ["--tickers", "NVDA", "--as-of-date", "2026-07-01", "--email"]
        )
    finally:
        get_settings.cache_clear()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "daily report email delivery failed: token expired" in captured.err
    assert len(delivery_provider.requests) == 1


def test_cli_does_not_send_email_when_email_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    composer = RecordingComposer(
        "Market Summary\n",
        html_body="<!doctype html>\n<html><body>Market Summary</body></html>\n",
    )

    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    exit_code = daily_report.main(["--tickers", "NVDA"])

    assert exit_code == 0
    assert capsys.readouterr().out == (
        "<!doctype html>\n<html><body>Market Summary</body></html>\n"
    )
    assert recording_app.report_delivery_provider is None


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
    assert capsys.readouterr().out == (
        "<!doctype html>\n<html><body>daily report body</body></html>\n"
    )
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
    assert capsys.readouterr().out == (
        "<!doctype html>\n<html><body>daily report body</body></html>\n"
    )
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
    output_path = tmp_path / "nested" / "custom.html"

    exit_code = daily_report.main(
        ["--tickers", "TSLA", "--output", str(output_path)]
    )

    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == (
        "<!doctype html>\n<html><body>daily report body</body></html>\n"
    )


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
        / "morning-investment-brief.html"
    )
    assert exit_code == 0
    assert archive_path.read_text(encoding="utf-8") == (
        "<!doctype html>\n<html><body>daily report body</body></html>\n"
    )


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
        / "evening-investment-review.html"
    )
    assert exit_code == 0
    assert archive_path.read_text(encoding="utf-8") == (
        "<!doctype html>\n<html><body>daily report body</body></html>\n"
    )


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
    output_path = tmp_path / "custom" / "daily-report.html"

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
        / "morning-investment-brief.html"
    )
    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == (
        "<!doctype html>\n<html><body>daily report body</body></html>\n"
    )
    assert archive_path.read_text(encoding="utf-8") == (
        "<!doctype html>\n<html><body>daily report body</body></html>\n"
    )


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
    output_path = tmp_path / "daily-report.html"

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
            "body_format": ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT,
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
    output_path = tmp_path / "daily-report.html"

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
    assert "<!doctype html>" in body
    assert "Morning Investment Brief" in body
    assert "Report Mode: morning" in body
    assert "Tickers: NVDA" in body
    assert "Factual evidence" in body
    assert "Track AI accelerator demand. Theme: AI infrastructure." in body
    assert "New Opportunities" in body
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
    output_path = tmp_path / "daily-report.html"

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


def test_cli_uses_configured_robinhood_holdings_when_tickers_are_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portfolio_service = RecordingPortfolioService(("aapl", "NVDA", "msft"))
    app = RecordingApp(
        portfolio_service=portfolio_service,
        portfolio_config=FakePortfolioConfig(provider="robinhood", account_id="default"),
    )
    composer = RecordingComposer("portfolio report\n")
    monkeypatch.setattr(daily_report, "create_app", lambda config: app)
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    exit_code = daily_report.main(["--output", str(tmp_path / "daily-report.html")])

    assert exit_code == 0
    assert portfolio_service.calls == ["default"]
    assert composer.calls == [
        {
            "tickers": ("AAPL", "NVDA", "MSFT"),
            "account_id": "default",
            "as_of_date": None,
            "mode": ReportMode.MORNING,
            "body_format": ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT,
        }
    ]


def test_cli_explicit_tickers_override_portfolio_holdings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portfolio_service = RecordingPortfolioService(("AAPL", "MSFT"))
    app = RecordingApp(
        portfolio_service=portfolio_service,
        portfolio_config=FakePortfolioConfig(provider="robinhood", account_id="default"),
    )
    composer = RecordingComposer("explicit report\n")
    monkeypatch.setattr(daily_report, "create_app", lambda config: app)
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda **kwargs: composer,
    )

    exit_code = daily_report.main(
        ["--tickers", "NVDA", "--output", str(tmp_path / "daily-report.html")]
    )

    assert exit_code == 0
    assert portfolio_service.calls == []
    assert composer.calls[0]["tickers"] == ("NVDA",)


def test_cli_evening_mode_renders_evening_report(tmp_path: Path) -> None:
    output_path = tmp_path / "evening-review.html"

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
    assert "<!doctype html>" in body
    assert "Evening Investment Review" in body
    assert "Report Mode: evening" in body
    assert "Position Cards" in body
    assert "Raw Evidence" in body


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


def test_portfolio_service_is_passed_into_daily_report_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portfolio_service = RecordingPortfolioService(("NVDA",))
    app = RecordingApp(portfolio_service=portfolio_service)
    received: list[object] = []

    class RecordingResearchService:
        def __init__(self, **kwargs: object) -> None:
            received.append(kwargs["portfolio_service"])

        def generate_report(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("report generation is not needed")

    monkeypatch.setattr(
        daily_report,
        "InvestmentResearchService",
        RecordingResearchService,
    )

    composer = daily_report._build_daily_report_composer(app)

    assert composer is not None
    assert received == [portfolio_service]


def test_report_includes_committee_opinion_sections(tmp_path: Path) -> None:
    output_path = tmp_path / "daily-report.html"

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
    assert "<!doctype html>" in body
    assert "1. Action Required" in body
    assert "2. Position Cards" in body
    assert "3. Stable Holdings" not in body
    assert "3. New Opportunities" in body
    assert "4. Market Overview" in body
    assert "5. Raw Evidence" in body
    assert "<strong>Dongdong:</strong>" in body
    assert "<strong>Xixi:</strong>" in body
    assert "<strong>Youyou:</strong>" in body
    assert "<strong>Final consensus:</strong>" in body
    assert "<strong>Confidence:</strong>" in body
    assert "Factual evidence" in body
    assert "Recommendations" not in body


def test_missing_tickers_without_watchlist_seed_return_clear_error(
    capsys: pytest.CaptureFixture[str],
    recording_app: RecordingApp,
) -> None:
    with pytest.raises(SystemExit) as exc:
        daily_report.main([])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert (
        "No tickers provided, no portfolio holdings found, "
        "and no watchlist seed is configured."
    ) in captured.err


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
