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


def test_cli_writes_report_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    composer = RecordingComposer("Market Summary\nCommittee Consensus\n")
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda: composer,
    )
    output_path = tmp_path / "daily-report.md"

    exit_code = daily_report.main(["--tickers", "NVDA", "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == (
        "Market Summary\nCommittee Consensus\n"
    )
    assert str(output_path) in capsys.readouterr().out


def test_default_output_path_works(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    composer = RecordingComposer()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda: composer,
    )

    exit_code = daily_report.main(["--tickers", "NVDA"])

    assert exit_code == 0
    assert (tmp_path / "reports" / "daily-report.md").read_text(
        encoding="utf-8"
    ) == "daily report body\n"


def test_custom_output_path_works(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    composer = RecordingComposer()
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda: composer,
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
) -> None:
    composer = RecordingComposer()
    monkeypatch.setattr(
        daily_report,
        "DailyInvestmentReportComposer",
        lambda: composer,
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


def test_report_includes_committee_opinion_sections(tmp_path: Path) -> None:
    output_path = tmp_path / "daily-report.md"

    exit_code = daily_report.main(
        ["--tickers", "NVDA", "--output", str(output_path)]
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


def test_missing_tickers_return_clear_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        daily_report.main([])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "--tickers" in captured.err


def test_invalid_tickers_return_clear_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        daily_report.main(["--tickers", "   "])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "at least one ticker is required" in captured.err
