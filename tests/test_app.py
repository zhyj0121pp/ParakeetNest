"""Tests for the application bootstrap container."""

from pathlib import Path

from parakeetnest.app import ParakeetNestApp, create_app, create_test_app
from parakeetnest.config import AppConfig
from parakeetnest.llm import MockLLMProvider


def test_create_app_returns_working_application(tmp_path: Path) -> None:
    """The app factory should centralize wiring for a runnable meeting."""
    app = create_app(AppConfig(database_path=tmp_path / "app.sqlite3"))
    try:
        result = app.meeting_service.run_meeting(
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
