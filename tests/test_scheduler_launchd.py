"""Tests for macOS launchd scheduling support."""

from __future__ import annotations

from pathlib import Path
import plistlib
import subprocess

import pytest

from parakeetnest.scheduler import (
    LaunchdInstaller,
    LaunchdPlistRenderer,
    LaunchdSchedule,
    ScheduleValidationError,
)


def test_default_plist_renders_daily_730_schedule(tmp_path: Path) -> None:
    """The default LaunchAgent should run daily at 7:30 AM local time."""
    script_path = tmp_path / "scripts" / "run_parakeetnest_daily.sh"
    script_path.parent.mkdir()
    script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    plist = LaunchdPlistRenderer().render(
        repo_root=tmp_path,
        script_path=script_path,
    )

    payload = plistlib.loads(plist.encode("utf-8"))
    assert payload["Label"] == "com.parakeetnest.daily"
    assert payload["StartCalendarInterval"] == {"Hour": 7, "Minute": 30}
    assert payload["ProgramArguments"] == [
        str(script_path.resolve()),
        "--mode",
        "morning",
    ]
    assert payload["WorkingDirectory"] == str(tmp_path.resolve())
    assert payload["RunAtLoad"] is False


@pytest.mark.parametrize(
    ("hour", "minute"),
    [(-1, 30), (24, 30), (7, -1), (7, 60)],
)
def test_schedule_validation_rejects_invalid_time(hour: int, minute: int) -> None:
    """launchd schedule fields should stay inside clock bounds."""
    with pytest.raises(ScheduleValidationError):
        LaunchdSchedule(hour=hour, minute=minute).validate()


def test_schedule_validation_accepts_clock_bounds() -> None:
    """Boundary clock values are valid."""
    LaunchdSchedule(hour=0, minute=0).validate()
    LaunchdSchedule(hour=23, minute=59).validate()


def test_plist_passes_evening_mode_to_runtime_script(tmp_path: Path) -> None:
    """The selected report mode should reach the runtime wrapper."""
    script_path = tmp_path / "scripts" / "run_parakeetnest_daily.sh"
    script_path.parent.mkdir()
    script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    plist = LaunchdPlistRenderer(report_mode="evening").render(
        repo_root=tmp_path,
        script_path=script_path,
    )

    payload = plistlib.loads(plist.encode("utf-8"))
    assert payload["ProgramArguments"] == [
        str(script_path.resolve()),
        "--mode",
        "evening",
    ]


def test_plist_rejects_invalid_report_mode(tmp_path: Path) -> None:
    """Only daily-report modes should be accepted by the scheduler."""
    script_path = tmp_path / "scripts" / "run_parakeetnest_daily.sh"
    script_path.parent.mkdir()
    script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    with pytest.raises(
        ScheduleValidationError,
        match="report mode must be morning or evening",
    ):
        LaunchdPlistRenderer(report_mode="overnight").render(
            repo_root=tmp_path,
            script_path=script_path,
        )


def test_install_command_construction_and_plist_write(tmp_path: Path) -> None:
    """Install should write the plist and construct launchctl commands."""
    calls: list[tuple[str, ...]] = []

    def runner(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(command))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    installer = LaunchdInstaller(
        label="com.parakeetnest.test",
        launch_agents_dir=tmp_path / "LaunchAgents",
        uid=501,
        runner=runner,
    )

    result = installer.install("<plist></plist>\n")

    assert result.plist_path == tmp_path / "LaunchAgents" / "com.parakeetnest.test.plist"
    assert result.plist_path.read_text(encoding="utf-8") == "<plist></plist>\n"
    assert calls == [
        ("launchctl", "bootout", "gui/501/com.parakeetnest.test"),
        (
            "launchctl",
            "bootstrap",
            "gui/501",
            str(result.plist_path),
        ),
    ]
    assert result.commands == tuple(calls)


def test_uninstall_command_construction_and_plist_removal(tmp_path: Path) -> None:
    """Uninstall should boot out and remove the plist if it exists."""
    calls: list[tuple[str, ...]] = []

    def runner(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(command))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    launch_agents_dir = tmp_path / "LaunchAgents"
    launch_agents_dir.mkdir()
    plist_path = launch_agents_dir / "com.parakeetnest.test.plist"
    plist_path.write_text("<plist></plist>\n", encoding="utf-8")
    installer = LaunchdInstaller(
        label="com.parakeetnest.test",
        launch_agents_dir=launch_agents_dir,
        uid=501,
        runner=runner,
    )

    result = installer.uninstall()

    assert result.plist_path == plist_path
    assert not plist_path.exists()
    assert calls == [("launchctl", "bootout", "gui/501/com.parakeetnest.test")]
    assert result.commands == tuple(calls)


def test_status_command_construction(tmp_path: Path) -> None:
    """Status should inspect the configured LaunchAgent label."""
    calls: list[tuple[str, ...]] = []

    def runner(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(command))
        return subprocess.CompletedProcess(command, 0, stdout="state = running\n", stderr="")

    installer = LaunchdInstaller(
        label="com.parakeetnest.test",
        launch_agents_dir=tmp_path / "LaunchAgents",
        uid=501,
        runner=runner,
    )

    status = installer.status()

    assert status.loaded is True
    assert status.stdout == "state = running\n"
    assert status.command == ("launchctl", "print", "gui/501/com.parakeetnest.test")
    assert calls == [status.command]


def test_plist_does_not_include_secrets_or_environment(tmp_path: Path) -> None:
    """Secrets should stay in runtime env loading, not in the plist."""
    script_path = tmp_path / "scripts" / "run_parakeetnest_daily.sh"
    script_path.parent.mkdir()
    script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    plist = LaunchdPlistRenderer().render(
        repo_root=tmp_path,
        script_path=script_path,
    )
    payload = plistlib.loads(plist.encode("utf-8"))

    assert "EnvironmentVariables" not in payload
    assert ".env" not in plist
    assert "OPENAI_API_KEY" not in plist
    assert "ROBINHOOD" not in plist
    assert "TOKEN" not in plist
    assert "PASSWORD" not in plist


def test_generated_plist_uses_absolute_paths(tmp_path: Path) -> None:
    """All plist filesystem paths should be absolute."""
    script_path = tmp_path / "scripts" / "run_parakeetnest_daily.sh"
    script_path.parent.mkdir()
    script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    payload = plistlib.loads(
        LaunchdPlistRenderer()
        .render(repo_root=tmp_path, script_path=script_path)
        .encode("utf-8")
    )

    assert Path(payload["ProgramArguments"][0]).is_absolute()
    assert Path(payload["WorkingDirectory"]).is_absolute()
    assert Path(payload["StandardOutPath"]).is_absolute()
    assert Path(payload["StandardErrorPath"]).is_absolute()
