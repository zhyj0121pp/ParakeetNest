"""Tests for the application bootstrap container."""

from pathlib import Path

import pytest

from parakeetnest.app import ParakeetNestApp, create_app, create_test_app
from parakeetnest.config import AppConfig
from parakeetnest.context import ContextRequest
from parakeetnest.exceptions import ConfigurationError
from parakeetnest.llm import MockLLMProvider
from parakeetnest.news import NewsQuery
from parakeetnest.sec import EdgarSecFilingProvider, MockSecFilingProvider


def test_create_app_returns_working_application(tmp_path: Path) -> None:
    """The app factory should centralize wiring for a runnable meeting."""
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        result = app.meeting_service.run(
            question="Should I watch POET?",
            ticker="POET",
        )
        app.commit()
    finally:
        app.close()

    assert isinstance(app, ParakeetNestApp)
    assert result.status.value == "completed"
    assert result.result_json is not None
    assert result.result_json["action"] == "watch"


def test_create_test_app_uses_mock_llm_provider() -> None:
    """The test factory should use an isolated database and mock LLM provider."""
    app = create_test_app()
    try:
        assert app.config.environment == "test"
        assert isinstance(app.llm_provider, MockLLMProvider)
    finally:
        app.close()


def test_create_app_can_disable_context_provider_before_service_creation(
    tmp_path: Path,
) -> None:
    """Provider config should be applied before ContextService receives providers."""
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            disabled_context_provider_ids=("news",),
        )
    )
    try:
        registrations = {
            registration.provider_id: registration.enabled
            for registration in app.context_provider_registry.list_registrations()
        }
        context = app.context_service.build_context(
            ContextRequest(question="Review AMD.", symbols=("AMD",))
        )
    finally:
        app.close()

    assert registrations["news"] is False
    assert registrations["market_data"] is True
    assert context.news is None
    assert context.market is not None


def test_create_app_wires_configured_news_service(tmp_path: Path) -> None:
    """The app factory should resolve the configured News Layer provider."""
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            news={"provider": "mock"},
        )
    )
    try:
        articles = app.news_service.get_news(NewsQuery(symbols=["POET"]))
    finally:
        app.close()

    assert len(articles) == 1
    assert articles[0].provider == "mock"
    assert articles[0].symbols == ["POET"]


def test_create_app_wires_news_context_provider_through_news_service(
    tmp_path: Path,
) -> None:
    """The context pipeline should receive news through NewsService."""
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            news={"provider": "mock"},
        )
    )
    try:
        context = app.context_service.build_context(
            ContextRequest(question="Review POET.", symbols=("POET",))
        )
    finally:
        app.close()

    assert context.news is not None
    assert context.news.source == "news"
    assert len(context.news.items) == 1
    assert context.news.items[0].symbol == "POET"


def test_create_app_defaults_to_mock_sec_filing_provider(tmp_path: Path) -> None:
    """The app factory should keep deterministic SEC filings as the default."""
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        context = app.context_service.build_context(
            ContextRequest(question="Review AAPL.", symbols=("AAPL",))
        )
    finally:
        app.close()

    assert isinstance(app.sec_filing_service._provider, MockSecFilingProvider)
    assert context.filings is not None
    assert context.filings.source == "sec_filings"
    assert context.filings.items[0].source == "mock"


def test_create_app_allows_mock_sec_filings_with_blank_edgar_user_agent(
    tmp_path: Path,
) -> None:
    """Blank SEC EDGAR identity should be ignored while mock filings are selected."""
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            sec_filings={
                "provider": "mock",
                "sec_edgar_user_agent": "   ",
            },
        )
    )
    try:
        provider = app.sec_filing_service._provider
    finally:
        app.close()

    assert isinstance(provider, MockSecFilingProvider)


def test_create_app_wires_sec_edgar_provider_when_configured(tmp_path: Path) -> None:
    """The app factory should resolve SEC EDGAR without making live requests."""
    app = create_app(
        AppConfig(
            database_path=tmp_path / "app.sqlite3",
            sec_filings={
                "provider": "sec_edgar",
                "sec_edgar_user_agent": "ParakeetNest tests test@example.com",
            },
        )
    )
    try:
        provider = app.sec_filing_service._provider
    finally:
        app.close()

    assert isinstance(provider, EdgarSecFilingProvider)


def test_create_app_rejects_sec_edgar_without_user_agent(tmp_path: Path) -> None:
    """SEC EDGAR requires an explicit app identity before bootstrap succeeds."""
    with pytest.raises(
        ConfigurationError,
        match="sec_filings.sec_edgar_user_agent",
    ):
        create_app(
            AppConfig(
                database_path=tmp_path / "app.sqlite3",
                sec_filings={
                    "provider": "sec_edgar",
                    "sec_edgar_user_agent": "   ",
                },
            )
        )
