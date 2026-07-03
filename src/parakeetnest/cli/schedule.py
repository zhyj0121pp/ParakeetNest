"""CLI commands for local macOS launchd scheduling."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from parakeetnest.scheduler import (
    DEFAULT_LABEL,
    LaunchdInstaller,
    LaunchdPlistRenderer,
    LaunchdSchedule,
    ScheduleValidationError,
)


def build_parser(
    *,
    prog: str = "parakeetnest schedule",
) -> argparse.ArgumentParser:
    """Build the scheduler CLI parser."""
    parser = argparse.ArgumentParser(prog=prog)
    subparsers = parser.add_subparsers(dest="schedule_command", required=True)

    install_parser = subparsers.add_parser(
        "install",
        help="Install the local macOS LaunchAgent.",
    )
    _add_common_schedule_args(install_parser)

    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Unload and remove the local macOS LaunchAgent.",
    )
    _add_label_arg(uninstall_parser)

    status_parser = subparsers.add_parser(
        "status",
        help="Show launchd status for the local LaunchAgent.",
    )
    _add_label_arg(status_parser)

    print_parser = subparsers.add_parser(
        "print-plist",
        help="Print the generated LaunchAgent plist.",
    )
    _add_common_schedule_args(print_parser)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the scheduler CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args, parser)


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Run a parsed scheduler command."""
    try:
        if args.schedule_command == "print-plist":
            print(_render_plist(args), end="")
            return 0

        installer = LaunchdInstaller(label=args.label)

        if args.schedule_command == "install":
            plist_content = _render_plist(args)
            result = installer.install(plist_content)
            print(f"installed: {result.plist_path}")
            for command in result.commands:
                print(f"ran: {' '.join(command)}")
            return 0

        if args.schedule_command == "uninstall":
            result = installer.uninstall()
            print(f"uninstalled: {result.plist_path}")
            for command in result.commands:
                print(f"ran: {' '.join(command)}")
            return 0

        if args.schedule_command == "status":
            status = installer.status()
            print(f"label: {status.label}")
            print(f"loaded: {str(status.loaded).lower()}")
            if status.stdout:
                print(status.stdout, end="" if status.stdout.endswith("\n") else "\n")
            if status.stderr:
                print(
                    status.stderr,
                    end="" if status.stderr.endswith("\n") else "\n",
                    file=sys.stderr,
                )
            return 0 if status.loaded else 1

    except ScheduleValidationError as exc:
        parser.error(str(exc))
    except OSError as exc:
        print(f"schedule command failed: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown schedule command: {args.schedule_command}")
    return 2


def _add_label_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--label",
        default=DEFAULT_LABEL,
        help=f"LaunchAgent label. Defaults to {DEFAULT_LABEL}.",
    )


def _add_common_schedule_args(parser: argparse.ArgumentParser) -> None:
    _add_label_arg(parser)
    parser.add_argument(
        "--hour",
        type=int,
        default=7,
        help="Local hour to run daily, 0-23. Defaults to 7.",
    )
    parser.add_argument(
        "--minute",
        type=int,
        default=30,
        help="Local minute to run daily, 0-59. Defaults to 30.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root used as the LaunchAgent working directory.",
    )
    parser.add_argument(
        "--script",
        type=Path,
        default=None,
        help="Daily runtime script path. Defaults to scripts/run_parakeetnest_daily.sh.",
    )


def _render_plist(args: argparse.Namespace) -> str:
    schedule = LaunchdSchedule(hour=args.hour, minute=args.minute)
    renderer = LaunchdPlistRenderer(label=args.label, schedule=schedule)
    return renderer.render(repo_root=args.repo_root, script_path=args.script)


if __name__ == "__main__":
    raise SystemExit(main())
