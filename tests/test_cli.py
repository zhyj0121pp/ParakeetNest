"""Tests for the local ParakeetNest CLI."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from parakeetnest import cli
from parakeetnest.committee import MeetingResult, MeetingStatus
from parakeetnest.context import ContextService
from parakeetnest.watchlist import (
    InMemoryWatchlistRepository,
    WatchlistContextProvider,
    WatchlistIntelligenceService,
)


def test_cli_parser_parses_meeting_question_and_ticker() -> None:
    """The meeting command should parse the question and ticker flag."""
    args = cli.build_parser().parse_args(
        ["meeting", "Should I buy POET now?", "--ticker", "POET"]
    )

    assert args.command == "meeting"
    assert args.question == "Should I buy POET now?"
    assert args.ticker == "POET"


def test_cli_parser_parses_watchlist_review_command() -> None:
    """The watchlist review command should be available in the root CLI."""
    args = cli.build_parser().parse_args(["watchlist", "review"])

    assert args.command == "watchlist"
    assert args.watchlist_command == "review"


def test_cli_parser_parses_watchlist_review_seed_path(tmp_path: Path) -> None:
    """The watchlist review command should accept a local seed path."""
    seed_path = tmp_path / "watchlist.json"
    args = cli.build_parser().parse_args(
        ["watchlist", "review", "--watchlist-seed", str(seed_path)]
    )

    assert args.command == "watchlist"
    assert args.watchlist_command == "review"
    assert args.watchlist_seed == seed_path


def test_cli_parser_parses_schedule_print_plist_command() -> None:
    """The schedule print-plist command should be available in the root CLI."""
    args = cli.build_parser().parse_args(
        ["schedule", "print-plist", "--hour", "8", "--minute", "15"]
    )

    assert args.command == "schedule"
    assert args.schedule_command == "print-plist"
    assert args.hour == 8
    assert args.minute == 15


def test_cli_parser_parses_daily_report_command(tmp_path: Path) -> None:
    """The daily report command should be available in the root CLI."""
    output_path = tmp_path / "morning.md"
    args = cli.build_parser().parse_args(
        [
            "daily-report",
            "--mode",
            "morning",
            "--tickers",
            "NVDA",
            "AAPL",
            "--output",
            str(output_path),
        ]
    )

    assert args.command == "daily-report"
    assert args.mode == "morning"
    assert args.tickers == ["NVDA", "AAPL"]
    assert args.output == output_path


def test_cli_daily_report_delegates_to_existing_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The root daily-report command should reuse the existing report CLI."""
    calls: list[list[str]] = []

    def recording_daily_report_main(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr(cli.daily_report, "main", recording_daily_report_main)

    exit_code = cli.main(
        [
            "daily-report",
            "--mode",
            "evening",
            "--tickers",
            "nvda",
            "--archive",
            "--email",
            "investor@example.com",
        ]
    )

    assert exit_code == 0
    assert calls == [
        [
            "--mode",
            "evening",
            "--tickers",
            "nvda",
            "--archive",
            "--email",
            "investor@example.com",
        ]
    ]


def test_cli_schedule_install_reports_launchctl_failure_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """launchctl failures should be reported as install errors, not tracebacks."""

    class FailingInstaller:
        def __init__(self, *, label: str) -> None:
            self.label = label

        def install(self, plist_content: str) -> object:
            raise subprocess.CalledProcessError(
                5,
                ["launchctl", "bootstrap", "gui/501", "agent.plist"],
                stderr="Bootstrap failed: 5\n",
            )

    monkeypatch.setattr(cli.schedule, "LaunchdInstaller", FailingInstaller)

    exit_code = cli.main(["schedule", "install"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "schedule command failed: launchctl bootstrap gui/501 agent.plist" in (
        captured.err
    )
    assert "Bootstrap failed: 5" in captured.err
    assert "Traceback" not in captured.err


def test_cli_meeting_command_calls_meeting_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI command should execute through create_app and MeetingService."""
    calls: list[tuple[str, str]] = []
    configs: list[object] = []

    class RecordingMeetingService:
        def run(self, question: str, ticker: str) -> MeetingResult:
            calls.append((question, ticker))
            return MeetingResult(
                meeting_id=42,
                status=MeetingStatus.COMPLETED,
                question=question,
                ticker=ticker,
                agent_results=(),
                result_json={"action": "watch"},
            )

    class RecordingApp:
        meeting_service = RecordingMeetingService()

        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            pass

    def recording_create_app(config: object) -> RecordingApp:
        configs.append(config)
        return RecordingApp()

    monkeypatch.setattr(cli, "create_app", recording_create_app)

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
    assert len(configs) == 1
    assert configs[0].database_path == tmp_path / "cli.sqlite3"
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


def test_cli_watchlist_review_empty_watchlist_succeeds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The watchlist review command should render an empty watchlist safely."""
    exit_code = cli.main(
        [
            "watchlist",
            "review",
            "--database",
            str(tmp_path / "watchlist-review.sqlite3"),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "## Watchlist" in output
    assert "- No watchlist insights available." in output


def test_cli_watchlist_review_with_seed_file_renders_seeded_symbols(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The watchlist review command should render items from a local seed file."""
    seed_path = tmp_path / "watchlist.json"
    seed_path.write_text(
        """
        [
          {
            "symbol": "NVDA",
            "company_name": "NVIDIA",
            "theme": "AI infrastructure",
            "reason": "Track AI accelerator demand",
            "priority": "high",
            "notes": ["Watch valuation risk"]
          }
        ]
        """,
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "watchlist",
            "review",
            "--database",
            str(tmp_path / "watchlist-review.sqlite3"),
            "--watchlist-seed",
            str(seed_path),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "## Watchlist" in output
    assert "- NVDA: Track AI accelerator demand. Theme: AI infrastructure." in output
    assert "Recommended action: review thesis" in output


def test_cli_watchlist_review_does_not_invoke_llm_or_committee_runtime(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Watchlist review should only build and render context."""
    repository = InMemoryWatchlistRepository()
    context_service = ContextService(
        providers=(
            WatchlistContextProvider(WatchlistIntelligenceService(repository)),
        )
    )
    calls: list[str] = []
    configs: list[object] = []

    class ForbiddenLLMProvider:
        def complete(self, request: object) -> object:
            raise AssertionError("LLM provider must not be invoked")

    class ForbiddenCommitteeRuntime:
        def run(self, agent: object, context: object) -> object:
            raise AssertionError("committee runtime must not be invoked")

    class ForbiddenMeetingService:
        def run(self, question: str, ticker: str) -> object:
            raise AssertionError("committee meeting must not be created")

    class RecordingApp:
        llm_provider = ForbiddenLLMProvider()
        agent_runtime = ForbiddenCommitteeRuntime()
        meeting_service = ForbiddenMeetingService()

        def __init__(self, context_service: ContextService) -> None:
            self.context_service = context_service

        def commit(self) -> None:
            raise AssertionError("watchlist review must not commit")

        def rollback(self) -> None:
            raise AssertionError("watchlist review must not rollback")

        def close(self) -> None:
            calls.append("close")

    def recording_create_app(config: object) -> RecordingApp:
        configs.append(config)
        return RecordingApp(context_service)

    monkeypatch.setattr(cli, "create_app", recording_create_app)

    exit_code = cli.main(["watchlist", "review"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == ["close"]
    assert len(configs) == 1
    assert configs[0].enabled_context_provider_ids == ("watchlist",)
    assert configs[0].watchlist_seed_path is None
    assert "## Watchlist" in output
    assert "- No watchlist insights available." in output
