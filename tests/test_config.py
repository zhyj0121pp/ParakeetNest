"""Tests for application configuration loading."""

from pathlib import Path

from parakeetnest.config import Settings, get_settings


def test_settings_defaults_are_safe() -> None:
    """Default settings should not contain secrets or require integrations."""
    settings = Settings(_env_file=None)

    assert settings.app_name == "ParakeetNest"
    assert settings.environment == "development"
    assert settings.openai_api_key is None
    assert settings.robinhood_password is None


def test_settings_load_from_prefixed_environment(monkeypatch) -> None:
    """Settings should load values from PARAKEETNEST-prefixed variables."""
    monkeypatch.setenv("PARAKEETNEST_ENVIRONMENT", "test")
    monkeypatch.setenv("PARAKEETNEST_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PARAKEETNEST_SQLITE_PATH", "tmp/test.sqlite3")
    monkeypatch.setenv("PARAKEETNEST_WATCHLIST_SEED_PATH", "tmp/watchlist.json")

    settings = Settings(_env_file=None)

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.sqlite_path == Path("tmp/test.sqlite3")
    assert settings.watchlist_seed_path == Path("tmp/watchlist.json")


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
