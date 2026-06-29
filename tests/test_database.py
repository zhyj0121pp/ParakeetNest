"""Tests for the SQLAlchemy database foundation."""

from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from parakeetnest.database import (
    Repository,
    create_session_factory,
    create_sqlite_engine,
    initialize_database,
    session_scope,
    table_names,
)
from parakeetnest.database.models import (
    CalendarEvent,
    CommitteeDiscussion,
    FinancialData,
    Holding,
    InvestmentThesis,
    MacroData,
    MarketData,
    NewsItem,
    Recommendation,
    Report,
    WatchlistItem,
)


def test_initialize_database_creates_v1_tables(tmp_path: Path) -> None:
    """Database initialization should create every v1 table."""
    engine = create_sqlite_engine(tmp_path / "parakeetnest.sqlite3")

    initialize_database(engine)

    inspector = inspect(engine)
    assert set(table_names()).issubset(set(inspector.get_table_names()))


def test_repository_create_get_and_list(tmp_path: Path) -> None:
    """The generic repository should support basic CRUD read paths."""
    engine = create_sqlite_engine(tmp_path / "repository.sqlite3")
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        repository = Repository(session, Holding)
        created = repository.create(
            Holding(
                symbol="NVDA",
                quantity=2.0,
                cost_basis=100.0,
                market_value=200.0,
                source="manual",
            )
        )

        fetched = repository.get(created.id)
        records = repository.list()

    assert fetched is not None
    assert fetched.symbol == "NVDA"
    assert len(records) == 1
    assert records[0].created_at is not None
    assert records[0].updated_at is not None


def test_repository_supports_knowledge_and_decision_models(tmp_path: Path) -> None:
    """Memory and decision records should persist simple JSON fields."""
    engine = create_sqlite_engine(tmp_path / "knowledge.sqlite3")
    initialize_database(engine)

    with Session(engine) as session:
        thesis_repository = Repository(session, InvestmentThesis)
        recommendation_repository = Repository(session, Recommendation)

        thesis = thesis_repository.create(
            InvestmentThesis(
                symbol="TSLA",
                thesis="Placeholder thesis for future committee review.",
                evidence=["vehicle delivery growth"],
                risks=["valuation risk"],
                catalysts=["new product cycle"],
                invalidation_conditions=["margin deterioration"],
            )
        )
        recommendation = recommendation_repository.create(
            Recommendation(
                symbol="TSLA",
                action="watch",
                confidence="low",
                horizon="3_months",
                evidence=[],
                risks=["insufficient validated evidence"],
                catalysts=[],
                data_confidence="low",
            )
        )
        session.commit()

        assert thesis_repository.get(thesis.id) is not None
        assert recommendation_repository.get(recommendation.id) is not None


def test_all_required_models_can_be_created(tmp_path: Path) -> None:
    """Representative required models should instantiate and persist cleanly."""
    engine = create_sqlite_engine(tmp_path / "required.sqlite3")
    initialize_database(engine)

    with Session(engine) as session:
        Repository(session, Holding).create(
            Holding(symbol="AMD", quantity=1.0, source="manual")
        )
        Repository(session, WatchlistItem).create(
            WatchlistItem(symbol="AMD", reason="AI accelerator watch", priority="high")
        )
        Repository(session, MarketData).create(
            MarketData(symbol="AMD", price=100.0, source="manual")
        )
        Repository(session, FinancialData).create(
            FinancialData(symbol="AMD", period="FY2026", revenue=1.0, source="manual")
        )
        Repository(session, NewsItem).create(
            NewsItem(title="AMD placeholder news", source="manual", symbol="AMD")
        )
        Repository(session, MacroData).create(
            MacroData(indicator="fed_funds_rate", value=1.0, source="manual")
        )
        Repository(session, CalendarEvent).create(
            CalendarEvent(event_type="earnings", title="AMD earnings", symbol="AMD")
        )
        Repository(session, InvestmentThesis).create(
            InvestmentThesis(
                symbol="AMD",
                thesis="Placeholder thesis.",
                evidence=[],
                risks=[],
                catalysts=[],
                invalidation_conditions=[],
            )
        )
        Repository(session, CommitteeDiscussion).create(
            CommitteeDiscussion(
                symbol="AMD",
                role="Yoyo",
                summary="Risk review placeholder.",
                evidence=[],
                risks=["competition"],
                catalysts=[],
            )
        )
        Repository(session, Recommendation).create(
            Recommendation(
                symbol="AMD",
                action="watch",
                confidence="low",
                horizon="3_months",
                evidence=[],
                risks=[],
                catalysts=[],
                data_confidence="low",
            )
        )
        Repository(session, Report).create(
            Report(
                report_type="daily",
                title="Daily Placeholder",
                content="Report content is pending committee workflow.",
                metadata_={"symbols": ["AMD"]},
            )
        )
        session.commit()

        assert len(Repository(session, Holding).list()) == 1
        assert len(Repository(session, WatchlistItem).list()) == 1
        assert len(Repository(session, MarketData).list()) == 1
        assert len(Repository(session, FinancialData).list()) == 1
        assert len(Repository(session, NewsItem).list()) == 1
        assert len(Repository(session, MacroData).list()) == 1
        assert len(Repository(session, CalendarEvent).list()) == 1
        assert len(Repository(session, InvestmentThesis).list()) == 1
        assert len(Repository(session, CommitteeDiscussion).list()) == 1
        assert len(Repository(session, Recommendation).list()) == 1
        assert len(Repository(session, Report).list()) == 1
