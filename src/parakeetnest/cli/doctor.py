"""Configuration-only integration diagnostics for ParakeetNest."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import tomllib
from typing import Any

from parakeetnest.config import AppConfig
from parakeetnest.email.gmail_auth import inspect_gmail_token
from parakeetnest.email import create_email_provider_registry
from parakeetnest.llm import create_llm_provider_registry
from parakeetnest.macro import create_macro_data_provider_registry
from parakeetnest.market_data import create_market_data_provider_registry
from parakeetnest.news import create_news_provider_registry
from parakeetnest.portfolio import create_portfolio_provider_registry
from parakeetnest.sec import create_sec_filing_provider_registry


@dataclass(frozen=True)
class ProviderCheck:
    """One doctor readiness check for a configured provider."""

    name: str
    provider: str
    configured: bool
    ready: bool
    details: tuple[str, ...] = ()


def build_parser(
    *,
    prog: str = "parakeetnest doctor",
) -> argparse.ArgumentParser:
    """Build the doctor command parser."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Validate provider configuration without calling external APIs.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        choices=("gmail",),
        help="Optional focused doctor check.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional TOML integration config. Defaults to mock AppConfig.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run provider configuration diagnostics."""
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_app_config(args.config) if args.config is not None else AppConfig()
    if args.target == "gmail":
        checks = (gmail_provider_check(config, os.environ),)
    else:
        checks = validate_provider_configuration(config, os.environ)
    print(format_doctor_report(config, checks))
    return 0 if all(check.ready for check in checks) else 1


def load_app_config(path: Path) -> AppConfig:
    """Load a provider-neutral TOML config into AppConfig."""
    raw_config = tomllib.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_config, dict):
        raise ValueError("integration config must be a TOML table")
    return AppConfig(**_known_app_config(raw_config))


def validate_provider_configuration(
    config: AppConfig,
    environ: Mapping[str, str],
) -> tuple[ProviderCheck, ...]:
    """Validate selected providers and required environment only."""
    return (
        _llm_check(config, environ),
        _market_data_check(config),
        _portfolio_check(config, environ),
        _sec_check(config, environ),
        _macro_check(config, environ),
        _email_check(config, environ),
        _news_check(config),
    )


def format_doctor_report(
    config: AppConfig,
    checks: tuple[ProviderCheck, ...],
) -> str:
    """Render doctor output for humans."""
    lines = [
        "ParakeetNest doctor",
        f"environment: {config.environment}",
        "configured providers:",
    ]
    for check in checks:
        status = "ready" if check.ready else "not ready"
        configured = "configured" if check.configured else "unknown provider"
        lines.append(f"- {check.name}: {check.provider} ({configured}, {status})")
        lines.extend(f"  - {detail}" for detail in check.details)
    return "\n".join(lines) + "\n"


def _llm_check(config: AppConfig, environ: Mapping[str, str]) -> ProviderCheck:
    provider = config.llm.provider
    configured = _is_registered(
        provider,
        (
            registration.provider_id
            for registration in create_llm_provider_registry().list_registrations()
        ),
    )
    details = []
    if _provider_is(provider, "openai"):
        details.extend(_env_present(environ, config.llm.api_key_env_var))
    return _check("llm", provider, configured, details)


def _market_data_check(config: AppConfig) -> ProviderCheck:
    provider = config.market_data.provider
    configured = _is_registered(
        provider,
        (
            registration.provider_id
            for registration in create_market_data_provider_registry().list_registrations()
        ),
    )
    return _check("market_data", provider, configured, ())


def _portfolio_check(
    config: AppConfig,
    environ: Mapping[str, str],
) -> ProviderCheck:
    provider = config.portfolio.provider
    configured = _is_registered(
        provider,
        (
            registration.provider_id
            for registration in create_portfolio_provider_registry().list_registrations()
        ),
    )
    details: list[str] = []
    if _provider_is(provider, "robinhood"):
        session_details = _env_present(
            environ,
            config.portfolio.robinhood_session_token_env_var,
        )
        username_details = _env_present(
            environ,
            config.portfolio.robinhood_username_env_var,
        )
        password_details = _env_present(
            environ,
            config.portfolio.robinhood_password_env_var,
        )
        cache_path = config.portfolio.robinhood_session_cache_path or environ.get(
            "ROBINHOOD_SESSION_CACHE_PATH"
        )
        cache_ready = bool(cache_path and Path(cache_path).expanduser().exists())
        if _env_ready(session_details) or (
            _env_ready(username_details) and _env_ready(password_details)
        ) or cache_ready:
            details.append("Robinhood credentials are configured.")
        else:
            details.extend(session_details + username_details + password_details)
            if cache_path:
                details.append("missing Robinhood session cache file.")
    return _check("portfolio", provider, configured, details)


def _sec_check(config: AppConfig, environ: Mapping[str, str]) -> ProviderCheck:
    provider = config.sec_filings.provider
    configured = _is_registered(
        provider,
        (
            registration.provider_id
            for registration in create_sec_filing_provider_registry(
                user_agent="ParakeetNest doctor doctor@example.com"
            ).list_registrations()
        ),
    )
    details: list[str] = []
    if _provider_is(provider, "edgar", "sec_edgar"):
        if config.sec_filings.user_agent:
            details.append("SEC User-Agent is configured.")
        else:
            details.extend(_env_present(environ, config.sec_filings.user_agent_env_var))
    return _check("sec", provider, configured, details)


def _macro_check(config: AppConfig, environ: Mapping[str, str]) -> ProviderCheck:
    provider = config.macro.provider
    configured = _is_registered(
        provider,
        (
            registration.provider_id
            for registration in create_macro_data_provider_registry().list_registrations()
        ),
    )
    details = []
    if _provider_is(provider, "fred"):
        details.extend(_env_present(environ, config.macro.fred_api_key_env_var))
    return _check("macro", provider, configured, details)


def _email_check(config: AppConfig, environ: Mapping[str, str]) -> ProviderCheck:
    provider = config.email.provider
    configured = _is_registered(
        provider,
        (
            registration.provider_id
            for registration in create_email_provider_registry().list_registrations()
        ),
    )
    if _provider_is(provider, "gmail"):
        return gmail_provider_check(config, environ, provider_configured=configured)
    details: list[str] = []
    return _check("email", provider, configured, details)


def gmail_provider_check(
    config: AppConfig,
    environ: Mapping[str, str],
    *,
    provider_configured: bool | None = None,
) -> ProviderCheck:
    """Validate local Gmail authorization files."""
    configured = (
        _is_registered(
            "gmail",
            (
                registration.provider_id
                for registration in create_email_provider_registry().list_registrations()
            ),
        )
        if provider_configured is None
        else provider_configured
    )
    status = inspect_gmail_token(
        credentials_path_env_var=config.email.gmail_credentials_path_env_var,
        token_path_env_var=config.email.gmail_token_path_env_var,
        environ=dict(environ),
    )
    return ProviderCheck(
        name="gmail",
        provider="gmail",
        configured=configured,
        ready=configured and status.ready,
        details=status.details,
    )


def _news_check(config: AppConfig) -> ProviderCheck:
    provider = config.news.provider
    configured = _is_registered(
        provider,
        (
            registration.provider_id
            for registration in create_news_provider_registry().list_registrations()
        ),
    )
    return _check("news", provider, configured, ())


def _check(
    name: str,
    provider: str,
    configured: bool,
    details: Sequence[str],
) -> ProviderCheck:
    missing = any(detail.startswith("missing ") for detail in details)
    return ProviderCheck(
        name=name,
        provider=provider,
        configured=configured,
        ready=configured and not missing,
        details=tuple(details),
    )


def _env_present(environ: Mapping[str, str], env_var_name: str) -> list[str]:
    env_var = env_var_name.strip()
    if env_var and environ.get(env_var, "").strip():
        return [f"{env_var} is set."]
    return [f"missing {env_var}."]


def _path_env_present(environ: Mapping[str, str], env_var_name: str) -> list[str]:
    details = _env_present(environ, env_var_name)
    if not _env_ready(details):
        return details
    path = Path(environ[env_var_name].strip()).expanduser()
    if path.exists():
        return [f"{env_var_name} points to an existing file."]
    return [f"missing file from {env_var_name}: {path}."]


def _env_ready(details: Sequence[str]) -> bool:
    return bool(details) and all(not detail.startswith("missing ") for detail in details)


def _is_registered(provider: str, provider_ids: Any) -> bool:
    normalized_provider = provider.strip().lower()
    return normalized_provider in {provider_id.strip().lower() for provider_id in provider_ids}


def _provider_is(provider: str, *provider_ids: str) -> bool:
    return provider.strip().lower() in {provider_id.strip().lower() for provider_id in provider_ids}


def _known_app_config(raw_config: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "database_path",
        "database_url",
        "watchlist_seed_path",
        "llm",
        "market_data",
        "news",
        "macro",
        "sec",
        "sec_filings",
        "financials",
        "portfolio",
        "email",
        "environment",
        "enabled_context_provider_ids",
        "disabled_context_provider_ids",
    }
    return {key: value for key, value in raw_config.items() if key in allowed_keys}


if __name__ == "__main__":
    raise SystemExit(main())
