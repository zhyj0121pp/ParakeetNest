"""Tests for application configuration loading."""

from pathlib import Path

from parakeetnest.config import (
    AppConfig,
    EmailConfig,
    LLMConfig,
    MacroConfig,
    MarketDataConfig,
    PortfolioConfig,
    Settings,
    email_config_from_settings,
    get_settings,
    llm_config_from_settings,
)


def test_settings_defaults_are_safe() -> None:
    """Default settings should not contain secrets or require integrations."""
    settings = Settings(_env_file=None)

    assert settings.app_name == "ParakeetNest"
    assert settings.environment == "development"
    assert settings.report_language == "en"
    assert settings.openai_api_key is None
    assert settings.robinhood_password is None


def test_settings_load_from_prefixed_environment(monkeypatch) -> None:
    """Settings should load values from PARAKEETNEST-prefixed variables."""
    monkeypatch.setenv("PARAKEETNEST_ENVIRONMENT", "test")
    monkeypatch.setenv("PARAKEETNEST_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PARAKEETNEST_SQLITE_PATH", "tmp/test.sqlite3")
    monkeypatch.setenv("PARAKEETNEST_WATCHLIST_SEED_PATH", "tmp/watchlist.json")
    monkeypatch.setenv("PARAKEETNEST_LLM_PROVIDER", "openai")
    monkeypatch.setenv("PARAKEETNEST_LLM_MODEL", "gpt-test-latest")
    monkeypatch.setenv("PARAKEETNEST_LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("PARAKEETNEST_LLM_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("PARAKEETNEST_LLM_MAX_COMPLETION_TOKENS", "250")

    settings = Settings(_env_file=None)

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.sqlite_path == Path("tmp/test.sqlite3")
    assert settings.watchlist_seed_path == Path("tmp/watchlist.json")
    assert settings.llm_provider == "openai"
    assert settings.llm_model == "gpt-test-latest"
    assert settings.llm_temperature == 0.2
    assert settings.llm_timeout_seconds == 45
    assert settings.llm_max_completion_tokens == 250


def test_settings_load_report_language_from_project_env_name(monkeypatch) -> None:
    """Report language follows the requested project-specific environment name."""
    monkeypatch.setenv("PARAKEET_REPORT_LANGUAGE", "zh")

    settings = Settings(_env_file=None)

    assert settings.report_language == "zh"


def test_settings_load_from_env_file(tmp_path: Path) -> None:
    """Settings should load local .env-style files without hard-coded secrets."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "PARAKEETNEST_APP_NAME=ParakeetNest Test",
                "PARAKEETNEST_ENVIRONMENT=test",
                "PARAKEETNEST_LOG_JSON=false",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "ParakeetNest Test"
    assert settings.environment == "test"
    assert settings.log_json is False


def test_empty_secret_values_are_ignored(tmp_path: Path) -> None:
    """Blank values in .env.example-style files should not become secrets."""
    env_file = tmp_path / ".env"
    env_file.write_text("PARAKEETNEST_OPENAI_API_KEY=\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.openai_api_key is None


def test_get_settings_cache_can_be_cleared(monkeypatch) -> None:
    """The settings cache should be clearable for tests."""
    get_settings.cache_clear()
    monkeypatch.setenv("PARAKEETNEST_ENVIRONMENT", "test")

    settings = get_settings()

    assert settings.environment == "test"
    get_settings.cache_clear()


def test_app_config_supports_llm_mapping() -> None:
    """App config should normalize provider-neutral LLM settings."""
    config = AppConfig(
        llm={
            "provider": "openai",
            "model": "gpt-test",
            "api_key_env_var": "PARAKEETNEST_TEST_OPENAI_API_KEY",
            "temperature": 0.1,
            "timeout_seconds": 30,
            "max_completion_tokens": 250,
        }
    )

    assert config.llm_provider == "openai"
    assert config.llm.provider == "openai"
    assert config.llm.model == "gpt-test"
    assert config.llm.api_key_env_var == "PARAKEETNEST_TEST_OPENAI_API_KEY"
    assert config.llm.temperature == 0.1
    assert config.llm.timeout_seconds == 30
    assert config.llm.max_completion_tokens == 250


def test_app_config_preserves_legacy_llm_provider_field() -> None:
    """Older llm_provider configuration should still select the provider."""
    config = AppConfig(llm_provider="mock")

    assert config.llm.provider == "mock"
    assert config.llm_provider == "mock"


def test_app_config_supports_market_data_mapping() -> None:
    """App config should normalize provider-neutral market data settings."""
    config = AppConfig(
        market_data={
            "provider": "yahoo",
            "max_attempts": 2,
            "retry_delay_seconds": 0.0,
        }
    )

    assert config.market_data == MarketDataConfig(
        provider="yahoo",
        max_attempts=2,
        retry_delay_seconds=0.0,
    )


def test_app_config_supports_macro_mapping() -> None:
    """App config should normalize provider-neutral macro settings."""
    config = AppConfig(
        macro={
            "provider": "fred",
            "fred_api_key_env_var": "TEST_FRED_API_KEY",
            "timeout": 2.5,
        }
    )

    assert config.macro == MacroConfig(
        provider="fred",
        fred_api_key_env_var="TEST_FRED_API_KEY",
        timeout=2.5,
    )


def test_app_config_supports_portfolio_mapping() -> None:
    """App config should normalize provider-neutral portfolio settings."""
    config = AppConfig(
        portfolio={
            "provider": "robinhood",
            "account_id": "default",
            "robinhood_session_cache_path": ".robinhood-session/robinhood.pickle",
            "robinhood_username_env_var": "TEST_RH_USER",
            "robinhood_password_env_var": "TEST_RH_PASS",
            "robinhood_session_token_env_var": "TEST_RH_SESSION",
        }
    )

    assert config.portfolio == PortfolioConfig(
        provider="robinhood",
        account_id="default",
        robinhood_session_cache_path=".robinhood-session/robinhood.pickle",
        robinhood_username_env_var="TEST_RH_USER",
        robinhood_password_env_var="TEST_RH_PASS",
        robinhood_session_token_env_var="TEST_RH_SESSION",
    )


def test_app_config_supports_email_mapping() -> None:
    """App config should normalize provider-neutral email settings."""
    config = AppConfig(
        email={
            "provider": "gmail",
            "gmail_credentials_path_env_var": "TEST_GOOGLE_CREDENTIALS",
            "gmail_token_path_env_var": "TEST_GMAIL_TOKEN",
            "sender_email": "sender@example.com",
        }
    )

    assert config.email == EmailConfig(
        provider="gmail",
        gmail_credentials_path_env_var="TEST_GOOGLE_CREDENTIALS",
        gmail_token_path_env_var="TEST_GMAIL_TOKEN",
        sender_email="sender@example.com",
    )


def test_settings_email_config_uses_gmail_when_paths_are_configured(
    monkeypatch,
) -> None:
    """Local Gmail path env vars should enable the Gmail email provider."""
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "secrets/gmail.json")
    monkeypatch.setenv("PARAKEETNEST_GMAIL_TOKEN_PATH", ".gmail-token/token.json")

    config = email_config_from_settings(Settings(_env_file=None))

    assert config.provider == "gmail"
    assert config.gmail_credentials_path_env_var == "GOOGLE_APPLICATION_CREDENTIALS"
    assert config.gmail_token_path_env_var == "PARAKEETNEST_GMAIL_TOKEN_PATH"


def test_settings_llm_config_uses_configured_provider_and_model(monkeypatch) -> None:
    """Local LLM env vars should select the configured LLM provider."""
    monkeypatch.setenv("PARAKEETNEST_LLM_PROVIDER", "openai")
    monkeypatch.setenv("PARAKEETNEST_LLM_MODEL", "gpt-test-latest")
    monkeypatch.setenv("PARAKEETNEST_LLM_API_KEY_ENV_VAR", "OPENAI_API_KEY")
    monkeypatch.setenv("PARAKEETNEST_LLM_TEMPERATURE", "0.1")
    monkeypatch.setenv("PARAKEETNEST_LLM_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("PARAKEETNEST_LLM_MAX_COMPLETION_TOKENS", "250")

    config = llm_config_from_settings(Settings(_env_file=None))

    assert config == LLMConfig(
        provider="openai",
        model="gpt-test-latest",
        api_key_env_var="OPENAI_API_KEY",
        temperature=0.1,
        timeout_seconds=45,
        max_completion_tokens=250,
    )
