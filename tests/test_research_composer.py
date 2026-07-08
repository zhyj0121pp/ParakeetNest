"""Tests for daily investment report composition."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from parakeetnest.config import get_settings
from parakeetnest.research import (
    DailyInvestmentReportComposer,
    InvestmentResearchReport,
    ReportBodyFormat,
    ReportMode,
    ResearchCatalyst,
    ResearchRisk,
    ResearchTickerReport,
    compose_daily_investment_report,
)


GENERATED_AT = datetime(2026, 7, 1, 15, 0, tzinfo=UTC)
AS_OF_DATE = date(2026, 7, 1)


@pytest.fixture(autouse=True)
def _english_report_language(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PARAKEET_REPORT_LANGUAGE", raising=False)
    monkeypatch.setenv("PARAKEETNEST_REPORT_LANGUAGE", "en")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class FakeResearchService:
    def __init__(self, report: InvestmentResearchReport) -> None:
        self.report = report
        self.calls: list[dict[str, object]] = []

    def generate_report(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
    ) -> InvestmentResearchReport:
        self.calls.append(
            {
                "tickers": tickers,
                "account_id": account_id,
                "as_of_date": as_of_date,
                "generated_at": generated_at,
                "mode": mode,
            }
        )
        return self.report


class FakeRenderer:
    def __init__(self) -> None:
        self.calls: list[InvestmentResearchReport] = []

    def render(self, report: InvestmentResearchReport) -> str:
        self.calls.append(report)
        return "<!doctype html>\n<html></html>\n"


def test_composer_generates_report_and_renders_html_body() -> None:
    report = _sample_report()
    service = FakeResearchService(report)
    renderer = FakeRenderer()
    composer = DailyInvestmentReportComposer(
        research_service=service,
        renderer=renderer,
    )

    body = composer.compose([" nvda "])

    assert body == "<!doctype html>\n<html></html>\n"
    assert service.calls == [
        {
            "tickers": [" nvda "],
            "account_id": None,
            "as_of_date": None,
            "generated_at": None,
            "mode": ReportMode.MORNING,
        }
    ]
    assert renderer.calls == [report]


def test_composer_accepts_only_interactive_html_attachment_format() -> None:
    report = _sample_report()
    service = FakeResearchService(report)
    renderer = FakeRenderer()
    composer = DailyInvestmentReportComposer(
        research_service=service,
        renderer=renderer,
    )

    body = composer.compose(
        ["NVDA"],
        body_format=ReportBodyFormat.INTERACTIVE_HTML_ATTACHMENT,
    )

    assert body == "<!doctype html>\n<html></html>\n"
    assert renderer.calls == [report]


def test_composer_passes_account_id_as_of_date_and_generated_at_through() -> None:
    report = _sample_report()
    service = FakeResearchService(report)
    composer = DailyInvestmentReportComposer(
        research_service=service,
        renderer=FakeRenderer(),
    )

    returned_report = composer.compose_report(
        ("NVDA", "AAPL"),
        account_id="main",
        as_of_date=AS_OF_DATE,
        generated_at=GENERATED_AT,
        mode=ReportMode.EVENING,
    )

    assert returned_report is report
    assert service.calls == [
        {
            "tickers": ("NVDA", "AAPL"),
            "account_id": "main",
            "as_of_date": AS_OF_DATE,
            "generated_at": GENERATED_AT,
            "mode": ReportMode.EVENING,
        }
    ]


def test_default_composer_can_generate_and_render_report_body() -> None:
    body = compose_daily_investment_report(("TSLA",), generated_at=GENERATED_AT)

    assert body.startswith("<!doctype html>\n<html>\n")
    assert "Morning Investment Brief" in body
    assert "Report Mode: morning" in body
    assert "Generated At: 2026-07-01T15:00:00+00:00" in body
    assert "Tickers: TSLA" in body
    assert "Recommendations" not in body
    assert "<strong>Final consensus:</strong>" in body


def test_default_composer_uses_permanent_committee_persona_names_and_roles() -> None:
    body = compose_daily_investment_report(("TSLA",), generated_at=GENERATED_AT)

    assert ">1. Action Required</h2>" in body
    assert ">2. Position Cards</h2>" in body
    assert ">3. Stable Holdings</h2>" in body
    assert ">4. New Opportunities</h2>" in body
    assert ">5. Market Overview</h2>" in body
    assert ">6. Raw Evidence</h2>" in body
    assert "<strong>Dongdong:</strong>" in body
    assert "<strong>Xixi:</strong>" in body
    assert "<strong>Youyou:</strong>" in body
    assert "<strong>Final consensus:</strong>" in body
    assert "<strong>Confidence:</strong>" in body


def _sample_report() -> InvestmentResearchReport:
    ticker_report = ResearchTickerReport(
        ticker="NVDA",
        summary="NVDA is included for daily research.",
        bull_case=("AI demand remains durable.",),
        bear_case=("Valuation risk remains elevated.",),
        risks=(ResearchRisk("Valuation risk remains elevated."),),
        catalysts=(ResearchCatalyst("AI demand remains durable."),),
    )
    return InvestmentResearchReport(
        ticker_reports=(ticker_report,),
        generated_at=GENERATED_AT,
    )
