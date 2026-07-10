"""Gmail OAuth token helpers for send-only delivery."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from parakeetnest.exceptions import ConfigurationError


GMAIL_SEND_SCOPES = ("https://www.googleapis.com/auth/gmail.send",)
GMAIL_REAUTH_MESSAGE = "Gmail authorization expired. Run: parakeet auth gmail"


@dataclass(frozen=True)
class GmailAuthPaths:
    """Configured local OAuth client and authorized-user token paths."""

    credentials_path: Path
    token_path: Path


@dataclass(frozen=True)
class GmailTokenStatus:
    """Local Gmail OAuth token readiness details."""

    credentials_exists: bool
    token_exists: bool
    refresh_token_exists: bool
    token_valid: bool | None
    details: tuple[str, ...]

    @property
    def ready(self) -> bool:
        """Return whether the local Gmail authorization is usable."""
        return (
            self.credentials_exists
            and self.token_exists
            and self.refresh_token_exists
            and self.token_valid is not False
        )


def resolve_gmail_auth_paths(
    *,
    credentials_path_env_var: str = "GOOGLE_APPLICATION_CREDENTIALS",
    token_path_env_var: str = "PARAKEETNEST_GMAIL_TOKEN_PATH",
    environ: Mapping[str, str] | None = None,
) -> GmailAuthPaths:
    """Resolve Gmail credential paths from configured environment variables."""
    env = environ if environ is not None else os.environ
    credentials_path = _required_env_path(
        env,
        credentials_path_env_var,
        "Gmail credentials file is not configured.",
    )
    token_path = _required_env_path(
        env,
        token_path_env_var,
        "Gmail token file is not configured.",
    )
    return GmailAuthPaths(credentials_path=credentials_path, token_path=token_path)


def reauthorize_gmail(
    *,
    credentials_path_env_var: str = "GOOGLE_APPLICATION_CREDENTIALS",
    token_path_env_var: str = "PARAKEETNEST_GMAIL_TOKEN_PATH",
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Delete any cached Gmail token, run OAuth, and save a fresh token."""
    paths = resolve_gmail_auth_paths(
        credentials_path_env_var=credentials_path_env_var,
        token_path_env_var=token_path_env_var,
        environ=environ,
    )
    if not paths.credentials_path.exists():
        raise ConfigurationError(
            f"Gmail credentials file does not exist: {paths.credentials_path}"
        )

    if paths.token_path.exists():
        paths.token_path.unlink()

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as error:
        raise ConfigurationError(
            "Gmail authorization requires the optional 'gmail' dependencies."
        ) from error

    flow = InstalledAppFlow.from_client_secrets_file(
        str(paths.credentials_path),
        scopes=list(GMAIL_SEND_SCOPES),
    )
    credentials = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )
    refresh_token = getattr(credentials, "refresh_token", None)
    if not refresh_token:
        raise ConfigurationError("Gmail OAuth did not return a refresh_token.")

    paths.token_path.parent.mkdir(parents=True, exist_ok=True)
    paths.token_path.write_text(credentials.to_json(), encoding="utf-8")
    return paths.token_path


def inspect_gmail_token(
    *,
    credentials_path_env_var: str = "GOOGLE_APPLICATION_CREDENTIALS",
    token_path_env_var: str = "PARAKEETNEST_GMAIL_TOKEN_PATH",
    environ: Mapping[str, str] | None = None,
) -> GmailTokenStatus:
    """Inspect local Gmail OAuth files without making external API calls."""
    try:
        paths = resolve_gmail_auth_paths(
            credentials_path_env_var=credentials_path_env_var,
            token_path_env_var=token_path_env_var,
            environ=environ,
        )
    except ConfigurationError as error:
        return GmailTokenStatus(
            credentials_exists=False,
            token_exists=False,
            refresh_token_exists=False,
            token_valid=False,
            details=(str(error), "If needed, run: parakeet auth gmail"),
        )

    details: list[str] = []
    credentials_exists = paths.credentials_path.exists()
    token_exists = paths.token_path.exists()
    if credentials_exists:
        details.append(f"Gmail credentials file exists: {paths.credentials_path}")
    else:
        details.append(f"missing Gmail credentials file: {paths.credentials_path}")
    if token_exists:
        details.append(f"Gmail token file exists: {paths.token_path}")
    else:
        details.append(f"missing Gmail token file: {paths.token_path}")
        details.append("If needed, run: parakeet auth gmail")
        return GmailTokenStatus(
            credentials_exists=credentials_exists,
            token_exists=False,
            refresh_token_exists=False,
            token_valid=False,
            details=tuple(details),
        )

    token_payload = _read_token_payload(paths.token_path)
    refresh_token_exists = bool(str(token_payload.get("refresh_token", "")).strip())
    if refresh_token_exists:
        details.append("Gmail token includes a refresh_token.")
    else:
        details.append("Gmail token is missing refresh_token. Run: parakeet auth gmail")

    token_valid = _token_valid(token_payload)
    if token_valid is False:
        details.append("Gmail token is invalid. Run: parakeet auth gmail")
    elif token_valid is True:
        details.append("Gmail token is marked valid.")
    else:
        details.append("Gmail token validity could not be verified locally.")

    return GmailTokenStatus(
        credentials_exists=credentials_exists,
        token_exists=token_exists,
        refresh_token_exists=refresh_token_exists,
        token_valid=token_valid,
        details=tuple(details),
    )


def is_invalid_grant_error(exc: BaseException) -> bool:
    """Return whether a Google exception indicates revoked or expired consent."""
    visited: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if "invalid_grant" in _exception_text(current).lower():
            return True
        current = current.__cause__ or current.__context__
    return False


def _required_env_path(
    environ: Mapping[str, str],
    env_var_name: str,
    error_message: str,
) -> Path:
    normalized_env_var = str(env_var_name).strip()
    if not normalized_env_var:
        raise ConfigurationError(error_message)
    value = environ.get(normalized_env_var, "")
    if not value.strip():
        raise ConfigurationError(f"{error_message} missing {normalized_env_var}.")
    return Path(value).expanduser()


def _read_token_payload(token_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _token_valid(token_payload: dict[str, Any]) -> bool | None:
    if "invalid" in token_payload:
        return not bool(token_payload["invalid"])
    if "valid" in token_payload:
        return bool(token_payload["valid"])
    if token_payload.get("error") == "invalid_grant":
        return False
    return None


def _exception_text(exc: BaseException) -> str:
    parts = [str(exc), exc.__class__.__name__]
    for attr_name in ("reason", "content"):
        value = getattr(exc, attr_name, None)
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        if value:
            parts.append(str(value))
    return " ".join(parts)


__all__ = [
    "GMAIL_REAUTH_MESSAGE",
    "GmailAuthPaths",
    "GmailTokenStatus",
    "inspect_gmail_token",
    "is_invalid_grant_error",
    "reauthorize_gmail",
    "resolve_gmail_auth_paths",
]
