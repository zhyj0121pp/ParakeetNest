"""End-to-end integration smoke tests for provider-neutral wiring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from parakeetnest import app as app_module
from parakeetnest.app import create_app
from parakeetnest.cli.daily_report import _build_daily_report_composer
from parakeetnest.config import AppConfig
from parakeetnest.email import create_email_provider_registry
from parakeetnest.llm import create_llm_provider_registry
from parakeetnest.macro import create_macro_data_provider_registry
from parakeetnest.market_data import create_market_data_provider_registry
from parakeetnest.market_data.models import (
    AssetType,
    CompanyInfo,
    MarketDataRange,
    MarketDataSnapshot,
    Symbol,
)
from parakeetnest.portfolio import create_portfolio_provider_registry
from parakeetnest.portfolio.models import (
    Holding,
    Portfolio,
    PortfolioHolding,
    PortfolioSnapshot,
)
from parakeetnest.reports import DailyReportOrchestrator, DailyReportRequest
from parakeetnest.research import ReportMode
from parakeetnest.sec import create_sec_filing_provider_registry
from parakeetnest.sec.models import SecFilingContent, SecFilingQuery


@dataclass
class _FakeRegistry:
    provider: Any

    def resolve(self, config: object) -> Any:
        return self.provider

    def get(self, provider_id: str) -> Any:
        return self.provider

    def get_provider(self, provider_id: str) -> Any:
        return self.provider


class FakeLLMProvider:
    name = "openai"

    def complete(self, request: object) -> object:
        raise AssertionError("integration smoke should not call external LLMs")


class FakeMarketDataProvider:
    provider_name = "yahoo"

    def __init__(self) -> None:
        self.snapshots: list[str] = []

    def supports(self, symbol: Symbol) -> bool:
        return bool(symbol.ticker)

    def get_snapshot(self, symbol: Symbol) -> MarketDataSnapshot:
        self.snapshots.append(symbol.ticker)
        return MarketDataSnapshot(
            symbol=symbol,
            asset_type=AssetType.STOCK,
            price=100.0,
            currency="USD",
            timestamp=datetime(2026, 7, 2, tzinfo=UTC),
            previous_close=99.0,
        )

    def get_company_info(self, symbol: Symbol) -> CompanyInfo:
        return CompanyInfo(symbol=symbol, name=f"{symbol.ticker} Inc.")

    def get_price_history(
        self,
        symbol: Symbol,
        data_range: MarketDataRange,
    ) -> list[object]:
        return []


class FakePortfolioProvider:
    provider_name = "robinhood"

    def __init__(self) -> None:
        self.snapshots: list[str] = []

    def list_accounts(self) -> tuple[str, ...]:
        return ("default",)

    def get_portfolio(self, account_id: str) -> Portfolio:
        return Portfolio(
            cash_balance=1000.0,
            total_market_value=2500.0,
            holdings=(
                Holding(
                    ticker="NVDA",
                    quantity=1,
                    market_value=2500.0,
                    portfolio_weight=1.0,
                    average_cost=2000.0,
                ),
            ),
        )

    def get_snapshot(self, account_id: str) -> PortfolioSnapshot:
        self.snapshots.append(account_id)
        return PortfolioSnapshot(
            account_id=account_id,
            as_of=datetime(2026, 7, 2, tzinfo=UTC),
            holdings=(
                PortfolioHolding(
                    symbol="NVDA",
                    name="NVIDIA",
                    quantity=1,
                    average_cost=2000.0,
                    current_price=2500.0,
                    sector="Technology",
                ),
            ),
            total_market_value=2500.0,
            total_equity=3500.0,
        )


class FakeSecProvider:
    provider_name = "edgar"

    def search_filings(self, query: SecFilingQuery) -> list[object]:
        return []

    def get_filing_content(self, accession_number: str) -> SecFilingContent:
        raise AssertionError("integration smoke should not fetch filing content")


class FakeMacroProvider:
    provider_name = "fred"

    def get_series(self, indicator_id: str, start_date=None, end_date=None) -> object:
        raise AssertionError("integration smoke should not call FRED")

    def get_latest(self, indicator_id: str) -> object | None:
        raise AssertionError("integration smoke should not call FRED")

    def get_snapshot(self, indicator_ids: list[str], as_of_date=None) -> object:
        raise AssertionError("integration smoke should not call FRED")


class FakeEmailProvider:
    provider_name = "gmail"

    def send(self, subject: str, body: str, recipient: str) -> None:
        raise AssertionError("integration smoke should not send email")


def test_create_app_wires_live_provider_configuration_without_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """create_app should resolve providers through registries and expose services."""
    llm_provider = FakeLLMProvider()
    market_provider = FakeMarketDataProvider()
    portfolio_provider = FakePortfolioProvider()
    sec_provider = FakeSecProvider()
    macro_provider = FakeMacroProvider()
    email_provider = FakeEmailProvider()

    monkeypatch.setattr(
        app_module,
        "create_llm_provider_registry",
        lambda: _FakeRegistry(llm_provider),
    )
    monkeypatch.setattr(
        app_module,
        "create_market_data_provider_registry",
        lambda: _FakeRegistry(market_provider),
    )
    monkeypatch.setattr(
        app_module,
        "create_portfolio_provider_registry",
        lambda: _FakeRegistry(portfolio_provider),
    )
    monkeypatch.setattr(
        app_module,
        "create_sec_filing_provider_registry",
        lambda **kwargs: _FakeRegistry(sec_provider),
    )
    monkeypatch.setattr(
        app_module,
        "create_macro_data_provider_registry",
        lambda: _FakeRegistry(macro_provider),
    )
    monkeypatch.setattr(
        app_module,
        "create_email_provider_registry",
        lambda: _FakeRegistry(email_provider),
    )

    app = create_app(_real_provider_config(tmp_path))
    try:
        registrations = {
            registration.provider_id: registration.provider
            for registration in app.context_provider_registry.list_registrations()
        }
    finally:
        app.close()

    assert app.llm_provider is llm_provider
    assert app.agent_runtime.llm_provider is llm_provider
    assert app.market_data_service._provider is market_provider
    assert registrations["market_data"]._market_data_service is app.market_data_service
    assert app.portfolio_provider is portfolio_provider
    assert registrations["portfolio"]._portfolio_provider is portfolio_provider
    assert app.sec_filing_service._provider is sec_provider
    assert registrations["sec_filings"]._sec_filing_service is app.sec_filing_service
    assert app.macro_data_service._provider is macro_provider
    assert registrations["macro"]._macro_data_service is app.macro_data_service
    assert app.email_provider is email_provider
    assert app.report_delivery_provider.email_provider is email_provider


def test_report_generation_path_is_complete_without_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Daily report generation should compose through configured app services."""
    portfolio_provider = FakePortfolioProvider()
    monkeypatch.setattr(
        app_module,
        "create_portfolio_provider_registry",
        lambda: _FakeRegistry(portfolio_provider),
    )

    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            portfolio={"provider": "robinhood", "account_id": "default"},
        )
    )
    try:
        orchestrator = DailyReportOrchestrator(
            composer=_build_daily_report_composer(app)
        )
        result = orchestrator.run(
            DailyReportRequest(
                mode=ReportMode.MORNING,
                tickers=("NVDA",),
                account_id="default",
                as_of_date=date(2026, 7, 2),
            )
        )
    finally:
        app.close()

    assert "Morning Investment Brief" in result.body
    assert "NVDA" in result.body
    assert portfolio_provider.snapshots == ["default"]


def test_provider_registries_advertise_completed_live_providers() -> None:
    """Registries should expose live provider IDs without network calls."""
    assert _provider_ids(create_llm_provider_registry()) >= {"mock", "openai"}
    assert _provider_ids(create_market_data_provider_registry()) >= {"mock", "yahoo"}
    assert _provider_ids(create_portfolio_provider_registry()) >= {
        "mock",
        "robinhood",
    }
    assert _provider_ids(
        create_sec_filing_provider_registry(
            user_agent="ParakeetNest tests test@example.com"
        )
    ) >= {"mock", "edgar", "sec_edgar"}
    assert _provider_ids(create_macro_data_provider_registry()) >= {"mock", "fred"}
    assert _provider_ids(create_email_provider_registry()) >= {"mock", "gmail"}


def _real_provider_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        database_path=tmp_path / "app.sqlite3",
        llm={"provider": "openai"},
        market_data={"provider": "yahoo"},
        portfolio={"provider": "robinhood", "account_id": "default"},
        sec={"provider": "edgar", "user_agent": "ParakeetNest tests test@example.com"},
        macro={"provider": "fred"},
        email={"provider": "gmail"},
    )


def _provider_ids(registry: object) -> set[str]:
    return {
        registration.provider_id
        for registration in registry.list_registrations()
    }
