"""Investment research report public API."""

from parakeetnest.research.composer import (
    DailyInvestmentReportComposer,
    compose_daily_investment_report,
)
from parakeetnest.research.models import (
    ConfidenceLevel,
    InvestmentResearchReport,
    RecommendationType,
    ResearchCatalyst,
    ResearchFinding,
    ResearchRecommendation,
    ResearchRisk,
    ResearchTickerReport,
)
from parakeetnest.research.rendering import (
    InvestmentResearchReportRenderer,
    render_investment_research_report,
)
from parakeetnest.research.service import InvestmentResearchService

__all__ = [
    "ConfidenceLevel",
    "DailyInvestmentReportComposer",
    "InvestmentResearchReport",
    "InvestmentResearchReportRenderer",
    "InvestmentResearchService",
    "RecommendationType",
    "ResearchCatalyst",
    "ResearchFinding",
    "ResearchRecommendation",
    "ResearchRisk",
    "ResearchTickerReport",
    "compose_daily_investment_report",
    "render_investment_research_report",
]
