"""Tests for the daily report CLI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from parakeetnest.cli import daily_report


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
    ) -> str:
        self.calls.append(
            {
                "tickers": tickers,
                "account_id": account_id,
                "as_of_date": as_of_date,
            }
        )
        return self.body


class EmptyWatchlistService:
    def build_all_insights(self) -> tuple[object, ...]:
        return ()

    def build_insight(self, symbol: str) -> object:
        raise ValueError(f"missing {symbol}")


class RecordingApp:
    def __init__(
        self,
        watchlist_service: object | None = None,
        intelligence_service: object | None = None,
    ) -> None:
        self.watchlist_intelligence_service = (
            watchlist_service or EmptyWatchlistService()
        )
        self.investment_intelligence_context_service = intelligence_service
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
    assert str(output_path) in capsys.readouterr().out


def test_default_output_path_works(
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

    exit_code = daily_report.main(["--tickers", "NVDA"])

    assert exit_code == 0
    assert (tmp_path / "reports" / "daily-report.md").read_text(
        encoding="utf-8"
    ) == "daily report body\n"


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
    assert "Tickers: NVDA" in body
    assert "Factual Ticker Context" in body
    assert "Track AI accelerator demand. Theme: AI infrastructure." in body
    assert "Watchlist Review" in body
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
    assert "Market Summary" in body
    assert "Portfolio Review" in body
    assert "Watchlist Review" in body
    assert "Dongdong's Opinion" in body
    assert "Xixi's Opinion" in body
    assert "Youyou's Opinion" in body
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
