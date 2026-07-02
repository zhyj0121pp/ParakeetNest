"""Application configuration for ParakeetNest."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
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
class MarketDataConfig:
    """Market data provider configuration."""

    provider: str = "mock"
    max_attempts: int = 3
    retry_delay_seconds: float = 0.1


@dataclass(frozen=True)
class NewsConfig:
    """News provider configuration."""

    provider: str = "mock"


@dataclass(frozen=True)
class SecFilingConfig:
    """SEC filing provider configuration."""

    provider: str = "mock"
    sec_edgar_user_agent: str | None = None


@dataclass(frozen=True)
class FinancialStatementConfig:
    """Financial statement provider configuration."""

    provider: str = "mock"


@dataclass(frozen=True)
class PortfolioConfig:
    """Portfolio provider configuration."""

    provider: str = "mock"
    account_id: str | None = None
    robinhood_username_env_var: str = "PARAKEETNEST_ROBINHOOD_USERNAME"
    robinhood_password_env_var: str = "PARAKEETNEST_ROBINHOOD_PASSWORD"
    robinhood_session_token_env_var: str = "PARAKEETNEST_ROBINHOOD_SESSION_TOKEN"


@dataclass(frozen=True)
class LLMConfig:
    """Language model provider configuration."""

    provider: str = "mock"
    model: str = "mock-committee"
    api_key_env_var: str = "OPENAI_API_KEY"
    temperature: float = 0.0


@dataclass(frozen=True)
class AppConfig:
    """Application container configuration."""

    database_path: Path | None = None
    database_url: str | None = None
    watchlist_seed_path: Path | None = None
    llm: LLMConfig | Mapping[str, str | float] = field(default_factory=LLMConfig)
    llm_provider: str | None = None
    market_data: MarketDataConfig | Mapping[str, str | int | float] = field(
        default_factory=MarketDataConfig
    )
    news: NewsConfig | Mapping[str, str] = field(default_factory=NewsConfig)
    sec_filings: SecFilingConfig | Mapping[str, str | None] = field(
        default_factory=SecFilingConfig
    )
    financials: FinancialStatementConfig | Mapping[str, str] = field(
        default_factory=FinancialStatementConfig
    )
    portfolio: PortfolioConfig | Mapping[str, str | None] = field(
        default_factory=PortfolioConfig
    )
    prompt_dir: Path = field(default_factory=lambda: DEFAULT_PROMPT_DIR)
    environment: AppEnvironmentName = "local"
    enabled_context_provider_ids: tuple[str, ...] | None = None
    disabled_context_provider_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Normalize nested configuration supplied as plain mappings."""
        if isinstance(self.llm, Mapping):
            object.__setattr__(
                self,
                "llm",
                LLMConfig(**dict(self.llm)),
            )
        if self.llm_provider is not None:
            object.__setattr__(
                self,
                "llm",
                replace(self.llm, provider=self.llm_provider),
            )
        object.__setattr__(self, "llm_provider", self.llm.provider)
        if isinstance(self.market_data, Mapping):
            object.__setattr__(
                self,
                "market_data",
                MarketDataConfig(**dict(self.market_data)),
            )
        if isinstance(self.news, Mapping):
            object.__setattr__(
                self,
                "news",
                NewsConfig(**dict(self.news)),
            )
        if isinstance(self.sec_filings, Mapping):
            object.__setattr__(
                self,
                "sec_filings",
                SecFilingConfig(**dict(self.sec_filings)),
            )
        if isinstance(self.financials, Mapping):
            object.__setattr__(
                self,
                "financials",
                FinancialStatementConfig(**dict(self.financials)),
            )
        if isinstance(self.portfolio, Mapping):
            object.__setattr__(
                self,
                "portfolio",
                PortfolioConfig(**dict(self.portfolio)),
            )

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
    watchlist_seed_path: Path | None = None

    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    robinhood_username: str | None = Field(default=None, repr=False)
    robinhood_password: SecretStr | None = Field(default=None, repr=False)
    fred_api_key: SecretStr | None = Field(default=None, repr=False)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
