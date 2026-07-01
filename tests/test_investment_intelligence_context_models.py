from __future__ import annotations

from datetime import UTC, datetime

from parakeetnest.intelligence.context import (
    InvestmentIntelligenceContext,
    MockInvestmentIntelligenceService,
)


def test_investment_intelligence_context_can_be_constructed() -> None:
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

    assert context.economic_regime is sample.economic_regime
    assert context.sector_rotation is sample.sector_rotation
    assert context.risk is sample.risk
    assert context.breadth is sample.breadth
    assert context.momentum is sample.momentum
    assert context.sentiment is sample.sentiment
    assert context.health is sample.health
    assert context.generated_at.isoformat() == "2026-06-30T21:00:00+00:00"


def test_context_package_exports_public_api() -> None:
    from parakeetnest.intelligence.context import (
        InvestmentIntelligenceRenderer,
        InvestmentIntelligenceService,
    )

    assert InvestmentIntelligenceContext is not None
    assert InvestmentIntelligenceRenderer is not None
    assert InvestmentIntelligenceService is not None
    assert MockInvestmentIntelligenceService is not None
