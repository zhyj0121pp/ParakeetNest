"""Authentication maintenance commands."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from parakeetnest.email.gmail_auth import reauthorize_gmail
from parakeetnest.exceptions import ConfigurationError


def build_parser(*, prog: str = "parakeetnest auth") -> argparse.ArgumentParser:
    """Build the auth command parser."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Refresh local provider authorization tokens.",
    )
    subparsers = parser.add_subparsers(dest="auth_command", required=True)
    subparsers.add_parser(
        "gmail",
        help="Regenerate the local Gmail OAuth token.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run authentication maintenance commands."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args, parser)


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Execute a parsed auth command."""
    if args.auth_command == "gmail":
        try:
            token_path = reauthorize_gmail()
        except ConfigurationError as error:
            parser.exit(1, f"gmail authorization failed: {error}\n")
        print(f"Gmail authorization refreshed. Token saved to: {token_path}")
        return 0
    parser.error(f"Unknown auth command: {args.auth_command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
