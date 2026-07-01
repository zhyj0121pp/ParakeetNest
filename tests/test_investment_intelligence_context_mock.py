from __future__ import annotations

from datetime import date

from parakeetnest.intelligence.context import (
    InvestmentIntelligenceContext,
    MockInvestmentIntelligenceService,
)


def test_mock_service_returns_valid_context() -> None:
    context = MockInvestmentIntelligenceService().build_context(
        as_of_date=date(2026, 6, 30),
        universe="us",
        symbol="qqq",
    )

    assert isinstance(context, InvestmentIntelligenceContext)
    assert context.economic_regime.as_of_date == date(2026, 6, 30)
    assert context.breadth.universe == "US"
    assert context.momentum.symbol == "QQQ"
    assert context.health.universe == "US"
    assert context.generated_at.isoformat() == "2026-06-30T21:00:00+00:00"
