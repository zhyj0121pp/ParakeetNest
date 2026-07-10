"""Tests for provider configuration diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from parakeetnest.cli import doctor
from parakeetnest.config import AppConfig


def test_doctor_defaults_to_ready_mock_mode(capsys) -> None:
    exit_code = doctor.main([])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "ParakeetNest doctor" in output
    assert "- llm: mock (configured, ready)" in output
    assert "- market_data: mock (configured, ready)" in output
    assert "- email: mock (configured, ready)" in output


def test_doctor_reports_missing_live_provider_environment(capsys, monkeypatch) -> None:
    for env_var in (
        "OPENAI_API_KEY",
        "FRED_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "PARAKEETNEST_GMAIL_TOKEN_PATH",
        "SEC_USER_AGENT",
        "ROBINHOOD_USERNAME",
        "ROBINHOOD_PASSWORD",
        "ROBINHOOD_SESSION_TOKEN",
    ):
        monkeypatch.delenv(env_var, raising=False)

    checks = doctor.validate_provider_configuration(
        AppConfig(
            llm={"provider": "openai", "api_key_env_var": "OPENAI_API_KEY"},
            market_data={"provider": "yahoo"},
            portfolio={
                "provider": "robinhood",
                "robinhood_username_env_var": "ROBINHOOD_USERNAME",
                "robinhood_password_env_var": "ROBINHOOD_PASSWORD",
                "robinhood_session_token_env_var": "ROBINHOOD_SESSION_TOKEN",
            },
            sec={"provider": "edgar", "user_agent_env_var": "SEC_USER_AGENT"},
            macro={"provider": "fred", "fred_api_key_env_var": "FRED_API_KEY"},
            email={
                "provider": "gmail",
                "gmail_credentials_path_env_var": "GOOGLE_APPLICATION_CREDENTIALS",
                "gmail_token_path_env_var": "PARAKEETNEST_GMAIL_TOKEN_PATH",
            },
        ),
        {},
    )
    print(doctor.format_doctor_report(AppConfig(), checks))

    output = capsys.readouterr().out
    assert any(check.name == "llm" and not check.ready for check in checks)
    assert any(check.name == "portfolio" and not check.ready for check in checks)
    assert "missing OPENAI_API_KEY" in output
    assert "missing ROBINHOOD_SESSION_TOKEN" in output
    assert "missing SEC_USER_AGENT" in output
    assert "missing FRED_API_KEY" in output
    assert "missing GOOGLE_APPLICATION_CREDENTIALS" in output


def test_doctor_loads_real_toml_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config-real.toml"
    config_path.write_text(
        """
        [llm]
        provider = "openai"
        api_key_env_var = "OPENAI_API_KEY"

        [market_data]
        provider = "yahoo"

        [news]
        provider = "yahoo"

        [portfolio]
        provider = "robinhood"
        robinhood_username_env_var = "ROBINHOOD_USERNAME"
        robinhood_password_env_var = "ROBINHOOD_PASSWORD"
        robinhood_session_token_env_var = "ROBINHOOD_SESSION_TOKEN"

        [sec]
        provider = "edgar"
        user_agent_env_var = "SEC_USER_AGENT"

        [macro]
        provider = "fred"
        fred_api_key_env_var = "FRED_API_KEY"

        [email]
        provider = "gmail"
        gmail_credentials_path_env_var = "GOOGLE_APPLICATION_CREDENTIALS"
        gmail_token_path_env_var = "PARAKEETNEST_GMAIL_TOKEN_PATH"
        """,
        encoding="utf-8",
    )

    config = doctor.load_app_config(config_path)

    assert config.llm.provider == "openai"
    assert config.market_data.provider == "yahoo"
    assert config.news.provider == "yahoo"
    assert config.portfolio.provider == "robinhood"
    assert config.sec_filings.provider == "edgar"
    assert config.macro.provider == "fred"
    assert config.email.provider == "gmail"


def test_root_cli_exposes_doctor_command(capsys) -> None:
    from parakeetnest import cli

    exit_code = cli.main(["doctor"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "ParakeetNest doctor" in output


def test_doctor_gmail_reports_missing_token_clearly(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    credentials_path = tmp_path / "credentials.json"
    token_path = tmp_path / "missing-token.json"
    credentials_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(credentials_path))
    monkeypatch.setenv("PARAKEETNEST_GMAIL_TOKEN_PATH", str(token_path))

    exit_code = doctor.main(["gmail"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "- gmail: gmail (configured, not ready)" in output
    assert f"missing Gmail token file: {token_path}" in output
    assert "run: parakeet auth gmail" in output


def test_doctor_gmail_reports_invalid_token_clearly(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    credentials_path = tmp_path / "credentials.json"
    token_path = tmp_path / "token.json"
    credentials_path.write_text("{}", encoding="utf-8")
    token_path.write_text(
        json.dumps({"refresh_token": "refresh-token-123", "invalid": True}),
        encoding="utf-8",
    )
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(credentials_path))
    monkeypatch.setenv("PARAKEETNEST_GMAIL_TOKEN_PATH", str(token_path))

    exit_code = doctor.main(["gmail"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Gmail token file exists" in output
    assert "Gmail token includes a refresh_token." in output
    assert "Gmail token is invalid. Run: parakeet auth gmail" in output
