"""Investment research report public API."""

from parakeetnest.research.composer import (
    DailyInvestmentReportComposer,
    ReportBodyFormat,
    compose_daily_investment_report,
)
from parakeetnest.research.delivery import (
    NoOpReportDeliveryProvider,
    ReportDeliveryAttachment,
    ReportDeliveryProvider,
    ReportDeliveryRequest,
    ReportDeliveryResult,
    ReportDeliveryService,
    ReportDeliveryStatus,
    ReportRecipient,
)
from parakeetnest.research.daily_delivery import (
    DailyReportDeliveryRequest,
    DailyReportDeliveryService,
)
from parakeetnest.research.localization import (
    ReportLanguage,
    ReportLocalization,
    get_configured_report_language,
    get_report_localization,
)
from parakeetnest.research.models import (
    InvestmentResearchReport,
    ReportMode,
    ResearchCatalyst,
    ResearchCommitteeConsensus,
    ResearchCommitteeOpinion,
    ResearchCommitteePortfolioView,
    ResearchFinding,
    ResearchRisk,
    ResearchTickerReport,
)
from parakeetnest.research.rendering import (
    InteractiveHtmlInvestmentResearchReportRenderer,
    render_investment_research_report_interactive_html,
)
from parakeetnest.research.service import InvestmentResearchService

__all__ = [
    "DailyInvestmentReportComposer",
    "DailyReportDeliveryRequest",
    "DailyReportDeliveryService",
    "InvestmentResearchReport",
    "InteractiveHtmlInvestmentResearchReportRenderer",
    "InvestmentResearchService",
    "NoOpReportDeliveryProvider",
    "ReportDeliveryAttachment",
    "ReportDeliveryProvider",
    "ReportDeliveryRequest",
    "ReportDeliveryResult",
    "ReportDeliveryService",
    "ReportDeliveryStatus",
    "ReportRecipient",
    "ReportBodyFormat",
    "ReportLanguage",
    "ReportLocalization",
    "ReportMode",
    "ResearchCatalyst",
    "ResearchCommitteeConsensus",
    "ResearchCommitteeOpinion",
    "ResearchCommitteePortfolioView",
    "ResearchFinding",
    "ResearchRisk",
    "ResearchTickerReport",
    "compose_daily_investment_report",
    "get_configured_report_language",
    "get_report_localization",
    "render_investment_research_report_interactive_html",
]
