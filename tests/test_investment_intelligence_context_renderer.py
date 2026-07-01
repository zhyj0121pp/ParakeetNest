from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.intelligence.context import (
    InvestmentIntelligenceRenderer,
    MockInvestmentIntelligenceService,
)
from parakeetnest.intelligence.context.models import InvestmentIntelligenceContext


def test_renderer_produces_deterministic_markdown_with_all_sections() -> None:
    sample = MockInvestmentIntelligenceService().build_context()
    context = InvestmentIntelligenceContext(
        economic_regime=sample.economic_regime,
        sector_rotation=sample.sector_rotation,
        risk=sample.risk,
        breadth=sample.breadth,
        momentum=sample.momentum,
        sentiment=sample.sentiment,
        health=sample.health,
        generated_at=datetime(2026, 6, 30, 21, 0, tzinfo=UTC),
    )
    renderer = InvestmentIntelligenceRenderer()

    markdown = renderer.render(context)

    assert markdown == renderer.render(context)
    assert "# Investment Intelligence Context" in markdown
    assert "Generated At: 2026-06-30T21:00:00+00:00" in markdown
    assert "## Economic Regime" in markdown
    assert "## Sector Rotation" in markdown
    assert "## Risk" in markdown
    assert "## Market Breadth" in markdown
    assert "## Momentum" in markdown
    assert "## Market Sentiment" in markdown
    assert "## Market Health" in markdown
    assert "- Regime: expansion" in markdown
    assert "- State: healthy" in markdown


def test_renderer_handles_optional_missing_fields_gracefully() -> None:
    context = MockInvestmentIntelligenceService().build_context()

    markdown = InvestmentIntelligenceRenderer().render(context)

    assert "None" not in markdown
    assert markdown.endswith("\n")
