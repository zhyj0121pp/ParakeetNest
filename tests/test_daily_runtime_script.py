"""Tests for the local daily-report runtime wrapper."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


SOURCE_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_parakeetnest_daily.sh"
)


def _build_test_repo(tmp_path: Path) -> Path:
    script_path = tmp_path / "scripts" / SOURCE_SCRIPT.name
    script_path.parent.mkdir()
    shutil.copy2(SOURCE_SCRIPT, script_path)

    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    python_path.chmod(0o755)
    return script_path


def test_runtime_script_forwards_evening_mode(tmp_path: Path) -> None:
    """An explicit evening mode should reach the daily-report CLI."""
    script_path = _build_test_repo(tmp_path)

    result = subprocess.run(
        [str(script_path), "--mode", "evening"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "-m",
        "parakeetnest.cli.daily_report",
        "--mode",
        "evening",
        "--archive",
    ]


def test_runtime_script_defaults_to_morning(tmp_path: Path) -> None:
    """Existing callers without a mode should keep the morning behavior."""
    script_path = _build_test_repo(tmp_path)

    result = subprocess.run(
        [str(script_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines()[2:5] == ["--mode", "morning", "--archive"]


def test_runtime_script_rejects_invalid_mode(tmp_path: Path) -> None:
    """Invalid report modes should fail before Python starts."""
    script_path = _build_test_repo(tmp_path)

    result = subprocess.run(
        [str(script_path), "--mode", "overnight"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "expected morning or evening" in result.stderr
