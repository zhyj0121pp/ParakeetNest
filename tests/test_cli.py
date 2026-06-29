"""Tests for the local ParakeetNest CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from parakeetnest import cli
from parakeetnest.committee import MeetingResult, MeetingStatus


def test_cli_parser_parses_meeting_question_and_ticker() -> None:
    """The meeting command should parse the question and ticker flag."""
    args = cli.build_parser().parse_args(
        ["meeting", "Should I buy POET now?", "--ticker", "POET"]
    )

    assert args.command == "meeting"
    assert args.question == "Should I buy POET now?"
    assert args.ticker == "POET"


def test_cli_meeting_command_calls_meeting_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI command should execute through MeetingService.run_meeting."""
    calls: list[tuple[str, str]] = []

    class RecordingMeetingService:
        def __init__(self, repository: object, orchestrator: object) -> None:
            self.repository = repository
            self.orchestrator = orchestrator

        def run_meeting(self, question: str, ticker: str) -> MeetingResult:
            calls.append((question, ticker))
            return MeetingResult(
                meeting_id=42,
                status=MeetingStatus.COMPLETED,
                question=question,
                ticker=ticker,
                agent_results=(),
                result_json={"action": "watch"},
            )

    monkeypatch.setattr(cli, "MeetingService", RecordingMeetingService)

    exit_code = cli.main(
        [
            "meeting",
            "Should I buy POET now?",
            "--ticker",
            "poet",
            "--database",
            str(tmp_path / "cli.sqlite3"),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == [("Should I buy POET now?", "POET")]
    assert "meeting_id: 42" in output
    assert "status: completed" in output


def test_cli_exits_successfully_with_mock_llm_provider(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The default mock provider should run an end-to-end local meeting."""
    exit_code = cli.main(
        [
            "meeting",
            "Should I buy POET now?",
            "--ticker",
            "POET",
            "--database",
            str(tmp_path / "mock.sqlite3"),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "meeting_id:" in output
    assert "status: completed" in output
    assert '"action": "watch"' in output
