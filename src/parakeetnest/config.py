"""Application configuration for ParakeetNest."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from functools import lru_cache
import os
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


EnvironmentName = Literal["development", "test", "production"]
AppEnvironmentName = Literal["test", "local", "prod"]
LogLevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ReportLanguageName = Literal["en", "zh"]


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
class MacroConfig:
    """Macro data provider configuration."""

    provider: str = "mock"
    fred_api_key_env_var: str = "FRED_API_KEY"
    timeout: float = 10.0


@dataclass(frozen=True)
class SecFilingConfig:
    """SEC filing provider configuration."""

    provider: str = "mock"
    user_agent: str | None = None
    user_agent_env_var: str = "SEC_USER_AGENT"
    timeout: float = 10.0
    sec_edgar_user_agent: str | None = None

    def __post_init__(self) -> None:
        """Preserve legacy SEC EDGAR config while supporting provider-neutral keys."""
        if self.user_agent is None and self.sec_edgar_user_agent is not None:
            object.__setattr__(self, "user_agent", self.sec_edgar_user_agent)
        if self.user_agent is None:
            env_var_name = self.user_agent_env_var.strip()
            if env_var_name:
                user_agent = os.environ.get(env_var_name)
                if user_agent is not None and user_agent.strip():
                    object.__setattr__(self, "user_agent", user_agent)


@dataclass(frozen=True)
class FinancialStatementConfig:
    """Financial statement provider configuration."""

    provider: str = "mock"


@dataclass(frozen=True)
class PortfolioConfig:
    """Portfolio provider configuration."""

    provider: str = "mock"
    account_id: str | None = None
    robinhood_session_cache_path: str | None = None
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
class EmailConfig:
    """Email delivery provider configuration."""

    provider: str = "mock"
    gmail_credentials_path_env_var: str = "GOOGLE_APPLICATION_CREDENTIALS"
    gmail_token_path_env_var: str = "PARAKEETNEST_GMAIL_TOKEN_PATH"
    sender_email: str | None = None


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
    macro: MacroConfig | Mapping[str, str | float] = field(default_factory=MacroConfig)
    sec: SecFilingConfig | Mapping[str, str | float | None] | None = None
    sec_filings: SecFilingConfig | Mapping[str, str | float | None] = field(
        default_factory=SecFilingConfig
    )
    financials: FinancialStatementConfig | Mapping[str, str] = field(
        default_factory=FinancialStatementConfig
    )
    portfolio: PortfolioConfig | Mapping[str, str | None] = field(
        default_factory=PortfolioConfig
    )
    email: EmailConfig | Mapping[str, str | None] = field(default_factory=EmailConfig)
    report_recipient_email: str | None = None
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
        if isinstance(self.macro, Mapping):
            object.__setattr__(
                self,
                "macro",
                MacroConfig(**dict(self.macro)),
            )
        if isinstance(self.sec_filings, Mapping):
            object.__setattr__(
                self,
                "sec_filings",
                SecFilingConfig(**dict(self.sec_filings)),
            )
        if self.sec is not None:
            sec_config = (
                SecFilingConfig(**dict(self.sec))
                if isinstance(self.sec, Mapping)
                else self.sec
            )
            object.__setattr__(self, "sec_filings", sec_config)
            object.__setattr__(self, "sec", sec_config)
        else:
            object.__setattr__(self, "sec", self.sec_filings)
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
        if isinstance(self.email, Mapping):
            object.__setattr__(
                self,
                "email",
                EmailConfig(**dict(self.email)),
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
    report_language: ReportLanguageName = Field(
        default="en",
        validation_alias=AliasChoices(
            "PARAKEET_REPORT_LANGUAGE",
            "PARAKEETNEST_REPORT_LANGUAGE",
        ),
    )

    data_dir: Path = Path("data")
    sqlite_path: Path = Path("data/parakeetnest.sqlite3")
    watchlist_seed_path: Path | None = None

    portfolio_provider: str = "mock"
    portfolio_account_id: str | None = None
    robinhood_session_cache_path: str | None = None
    robinhood_username_env_var: str = "PARAKEETNEST_ROBINHOOD_USERNAME"
    robinhood_password_env_var: str = "PARAKEETNEST_ROBINHOOD_PASSWORD"
    robinhood_session_token_env_var: str = "PARAKEETNEST_ROBINHOOD_SESSION_TOKEN"

    email_provider: str = "mock"
    gmail_credentials_path_env_var: str = "GOOGLE_APPLICATION_CREDENTIALS"
    gmail_token_path_env_var: str = "PARAKEETNEST_GMAIL_TOKEN_PATH"
    sender_email: str | None = None
    report_recipient: str | None = None

    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    robinhood_username: str | None = Field(default=None, repr=False)
    robinhood_password: SecretStr | None = Field(default=None, repr=False)
    fred_api_key: SecretStr | None = Field(default=None, repr=False)


def portfolio_config_from_settings(settings: Settings) -> PortfolioConfig:
    """Build provider-neutral portfolio config from local settings."""
    legacy_username_env_var = "ROBINHOOD_USERNAME"
    legacy_password_env_var = "ROBINHOOD_PASSWORD"
    legacy_session_token_env_var = "ROBINHOOD_SESSION_TOKEN"
    legacy_session_cache_path_env_var = "ROBINHOOD_SESSION_CACHE_PATH"
    legacy_robinhood_configured = any(
        _read_nonempty_env(env_var_name)
        for env_var_name in (
            legacy_username_env_var,
            legacy_password_env_var,
            legacy_session_token_env_var,
            legacy_session_cache_path_env_var,
        )
    )
    provider = settings.portfolio_provider
    if provider == "mock" and legacy_robinhood_configured:
        provider = "robinhood"
    return PortfolioConfig(
        provider=provider,
        account_id=settings.portfolio_account_id,
        robinhood_session_cache_path=(
            settings.robinhood_session_cache_path
            or _read_nonempty_env(legacy_session_cache_path_env_var)
        ),
        robinhood_username_env_var=(
            legacy_username_env_var
            if _read_nonempty_env(legacy_username_env_var)
            else settings.robinhood_username_env_var
        ),
        robinhood_password_env_var=(
            legacy_password_env_var
            if _read_nonempty_env(legacy_password_env_var)
            else settings.robinhood_password_env_var
        ),
        robinhood_session_token_env_var=(
            legacy_session_token_env_var
            if _read_nonempty_env(legacy_session_token_env_var)
            else settings.robinhood_session_token_env_var
        ),
    )


def email_config_from_settings(settings: Settings) -> EmailConfig:
    """Build provider-neutral email config from local settings."""
    provider = settings.email_provider
    if (
        provider == "mock"
        and _read_nonempty_env(settings.gmail_credentials_path_env_var)
        and _read_nonempty_env(settings.gmail_token_path_env_var)
    ):
        provider = "gmail"
    return EmailConfig(
        provider=provider,
        gmail_credentials_path_env_var=settings.gmail_credentials_path_env_var,
        gmail_token_path_env_var=settings.gmail_token_path_env_var,
        sender_email=settings.sender_email,
    )


def default_portfolio_account_id(config: PortfolioConfig) -> str | None:
    """Return the default account id for a configured portfolio provider."""
    if config.account_id is not None:
        account_id = config.account_id.strip()
        if account_id:
            return account_id
    if config.provider.strip().lower() == "robinhood":
        return "default"
    return None


def _read_nonempty_env(env_var_name: str) -> str | None:
    value = os.getenv(env_var_name)
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
