"""Application configuration for ParakeetNest."""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


EnvironmentName = Literal["development", "test", "production"]
AppEnvironmentName = Literal["test", "local", "prod"]
LogLevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


DEFAULT_PROMPT_DIR = Path(__file__).parent / "committee" / "prompts"


@dataclass(frozen=True)
class AppConfig:
    """Application container configuration."""

    database_path: Path | None = None
    database_url: str | None = None
    llm_provider: str = "mock"
    prompt_dir: Path = field(default_factory=lambda: DEFAULT_PROMPT_DIR)
    environment: AppEnvironmentName = "local"

    def resolved_database_url(self) -> str:
        """Return the configured SQLAlchemy database URL."""
        if self.database_url is not None:
            return self.database_url
        database_path = self.database_path or get_settings().sqlite_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{database_path}"


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PARAKEETNEST_",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_name: str = "ParakeetNest"
    environment: EnvironmentName = "development"
    log_level: LogLevelName = "INFO"
    log_json: bool = True

    data_dir: Path = Path("data")
    sqlite_path: Path = Path("data/parakeetnest.sqlite3")

    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    robinhood_username: str | None = Field(default=None, repr=False)
    robinhood_password: SecretStr | None = Field(default=None, repr=False)
    fred_api_key: SecretStr | None = Field(default=None, repr=False)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
