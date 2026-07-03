"""macOS launchd scheduling primitives for local ParakeetNest runs."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import plistlib
import subprocess
from typing import Protocol


DEFAULT_LABEL = "com.parakeetnest.daily"
DEFAULT_HOUR = 7
DEFAULT_MINUTE = 30
DEFAULT_SCRIPT_RELATIVE_PATH = Path("scripts/run_parakeetnest_daily.sh")


class ScheduleValidationError(ValueError):
    """Raised when a launchd schedule cannot be rendered safely."""


@dataclass(frozen=True)
class LaunchdSchedule:
    """Daily local launchd schedule for the ParakeetNest runtime wrapper."""

    hour: int = DEFAULT_HOUR
    minute: int = DEFAULT_MINUTE

    def validate(self) -> None:
        """Validate launchd-compatible time fields."""
        if not 0 <= self.hour <= 23:
            raise ScheduleValidationError("hour must be between 0 and 23")
        if not 0 <= self.minute <= 59:
            raise ScheduleValidationError("minute must be between 0 and 59")

    def to_start_calendar_interval(self) -> dict[str, int]:
        """Return launchd StartCalendarInterval fields."""
        self.validate()
        return {"Hour": self.hour, "Minute": self.minute}


@dataclass(frozen=True)
class LaunchdPlistRenderer:
    """Render a LaunchAgent plist for running the existing daily runtime script."""

    label: str = DEFAULT_LABEL
    schedule: LaunchdSchedule = LaunchdSchedule()

    def render(
        self,
        *,
        repo_root: Path,
        script_path: Path | None = None,
        stdout_path: Path | None = None,
        stderr_path: Path | None = None,
    ) -> str:
        """Render the LaunchAgent plist as XML."""
        repo_root = _absolute_path(repo_root, field_name="repo_root")
        resolved_script = _absolute_path(
            script_path or repo_root / DEFAULT_SCRIPT_RELATIVE_PATH,
            field_name="script_path",
        )
        resolved_stdout = _absolute_path(
            stdout_path or repo_root / "logs" / "parakeetnest-daily.out.log",
            field_name="stdout_path",
        )
        resolved_stderr = _absolute_path(
            stderr_path or repo_root / "logs" / "parakeetnest-daily.err.log",
            field_name="stderr_path",
        )
        self.schedule.validate()

        payload = {
            "Label": self.label,
            "ProgramArguments": [str(resolved_script)],
            "WorkingDirectory": str(repo_root),
            "StartCalendarInterval": self.schedule.to_start_calendar_interval(),
            "StandardOutPath": str(resolved_stdout),
            "StandardErrorPath": str(resolved_stderr),
            "RunAtLoad": False,
        }
        return plistlib.dumps(payload, sort_keys=True).decode("utf-8")


class CommandRunner(Protocol):
    """Protocol for subprocess-compatible command runners."""

    def __call__(
        self,
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command and return a completed process."""


@dataclass(frozen=True)
class LaunchdInstallResult:
    """Result of writing and loading a LaunchAgent."""

    plist_path: Path
    commands: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class LaunchdStatus:
    """LaunchAgent status output from launchctl."""

    label: str
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def loaded(self) -> bool:
        """Whether launchctl found the agent."""
        return self.returncode == 0


class LaunchdInstaller:
    """Install, uninstall, and inspect a user LaunchAgent."""

    def __init__(
        self,
        *,
        label: str = DEFAULT_LABEL,
        launch_agents_dir: Path | None = None,
        uid: int | None = None,
        runner: CommandRunner | None = None,
    ) -> None:
        self.label = label
        self.launch_agents_dir = launch_agents_dir or (
            Path.home() / "Library" / "LaunchAgents"
        )
        self.uid = uid if uid is not None else os.getuid()
        self.runner = runner or subprocess.run

    @property
    def plist_path(self) -> Path:
        """Return the conventional user LaunchAgent plist path."""
        return self.launch_agents_dir / f"{self.label}.plist"

    def install(self, plist_content: str) -> LaunchdInstallResult:
        """Write the LaunchAgent plist and load it for the current GUI user."""
        plist_path = self.plist_path
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(plist_content, encoding="utf-8")
        commands = (
            self.bootout_command(),
            self.bootstrap_command(plist_path),
        )
        self._run(commands[0], check=False)
        self._run(commands[1], check=True)
        return LaunchdInstallResult(plist_path=plist_path, commands=commands)

    def uninstall(self) -> LaunchdInstallResult:
        """Unload and remove the user LaunchAgent plist if present."""
        plist_path = self.plist_path
        commands = (self.bootout_command(),)
        self._run(commands[0], check=False)
        if plist_path.exists():
            plist_path.unlink()
        return LaunchdInstallResult(plist_path=plist_path, commands=commands)

    def status(self) -> LaunchdStatus:
        """Return launchctl status for the configured LaunchAgent label."""
        command = self.print_command()
        result = self._run(command, check=False)
        return LaunchdStatus(
            label=self.label,
            command=command,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def bootstrap_command(self, plist_path: Path | None = None) -> tuple[str, ...]:
        """Build the launchctl bootstrap command."""
        return (
            "launchctl",
            "bootstrap",
            f"gui/{self.uid}",
            str(plist_path or self.plist_path),
        )

    def bootout_command(self) -> tuple[str, ...]:
        """Build the launchctl bootout command."""
        return ("launchctl", "bootout", f"gui/{self.uid}/{self.label}")

    def print_command(self) -> tuple[str, ...]:
        """Build the launchctl status command."""
        return ("launchctl", "print", f"gui/{self.uid}/{self.label}")

    def _run(
        self,
        command: tuple[str, ...],
        *,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        return self.runner(
            list(command),
            check=check,
            capture_output=True,
            text=True,
        )


def _absolute_path(path: Path, *, field_name: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_absolute():
        raise ScheduleValidationError(f"{field_name} must be an absolute path")
    return resolved
