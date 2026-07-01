"""Committee members and meeting orchestration."""

from parakeetnest.committee.agents import (
    ChairmanAgent,
    DongdongAgent,
    XixiAgent,
    YoyoAgent,
)
from parakeetnest.committee.base import CommitteeAgent, CommitteeMember
from parakeetnest.committee.chairman import Chairman
from parakeetnest.committee.dongdong import Dongdong
from parakeetnest.committee.judgment import CommitteeJudgmentService
from parakeetnest.committee.models import (
    AgentResult,
    ChairmanSummary,
    CommitteeMeetingResult,
    CommitteeOpinion,
    DEFAULT_INVESTMENT_COMMITTEE,
    InvestmentContext,
    InvestmentCommitteeDecision,
    InvestmentCommitteeMember,
    InvestmentCommitteeReport,
    InvestmentCommitteeRequest,
    MeetingContext,
    MeetingRequest,
    MeetingResult,
    MeetingStatus,
)
from parakeetnest.committee.personas import (
    CommitteeMemberProfile,
    CommitteeOpinionStyle,
    CommitteePersona,
    CommitteePersonaRegistry,
    CommitteeRole,
    DAILY_INVESTMENT_COMMITTEE,
    DONGDONG_PERSONA,
    DuplicateCommitteePersonaError,
    PERMANENT_COMMITTEE_PERSONAS,
    PermanentCommitteeService,
    UnknownCommitteePersonaError,
    XIXI_PERSONA,
    YOUYOU_PERSONA,
    create_permanent_committee_service,
)
from parakeetnest.committee.prompting import (
    ADVISORY_ONLY_DISCLAIMER,
    CommitteePersonaPrompt,
    CommitteePromptBuilder,
    CommitteePromptContext,
    PersonaDrivenCommitteePromptBuilder,
)
from parakeetnest.committee.secretary import InvestmentSecretary
from parakeetnest.committee.xixi import Xixi
from parakeetnest.committee.yoyo import Yoyo


def __getattr__(name: str) -> object:
    """Lazily expose runtime exports without loading them for domain imports."""
    if name in {"AgentRuntime", "PromptRenderer"}:
        from parakeetnest.committee.runtime import AgentRuntime, PromptRenderer

        exports = {
            "AgentRuntime": AgentRuntime,
            "PromptRenderer": PromptRenderer,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Chairman",
    "ChairmanAgent",
    "ChairmanSummary",
    "CommitteeAgent",
    "CommitteeJudgmentService",
    "CommitteeMemberProfile",
    "CommitteeMember",
    "CommitteeMeetingResult",
    "CommitteeOpinionStyle",
    "CommitteeOpinion",
    "CommitteePersona",
    "CommitteePersonaRegistry",
    "CommitteeRole",
    "DAILY_INVESTMENT_COMMITTEE",
    "DEFAULT_INVESTMENT_COMMITTEE",
    "DONGDONG_PERSONA",
    "Dongdong",
    "DongdongAgent",
    "DuplicateCommitteePersonaError",
    "InvestmentContext",
    "InvestmentCommitteeDecision",
    "InvestmentCommitteeMember",
    "InvestmentCommitteeReport",
    "InvestmentCommitteeRequest",
    "InvestmentSecretary",
    "AgentResult",
    "AgentRuntime",
    "ADVISORY_ONLY_DISCLAIMER",
    "CommitteePersonaPrompt",
    "CommitteePromptBuilder",
    "CommitteePromptContext",
    "MeetingContext",
    "MeetingRequest",
    "MeetingResult",
    "MeetingStatus",
    "PERMANENT_COMMITTEE_PERSONAS",
    "PermanentCommitteeService",
    "PersonaDrivenCommitteePromptBuilder",
    "PromptRenderer",
    "UnknownCommitteePersonaError",
    "Xixi",
    "XixiAgent",
    "XIXI_PERSONA",
    "YOUYOU_PERSONA",
    "Yoyo",
    "YoyoAgent",
    "create_permanent_committee_service",
]
