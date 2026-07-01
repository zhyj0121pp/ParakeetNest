"""Initial committee agent profiles."""

from __future__ import annotations

from parakeetnest.committee.agent_profiles.models import (
    AgentContextRequirement,
    AgentMemoryPolicy,
    AgentOutputSchema,
    AgentProfile,
    AgentRole,
)


RECOMMENDATION_FIELDS: tuple[str, ...] = (
    "action",
    "confidence",
    "horizon",
    "evidence",
    "risks",
    "catalysts",
)

COMMITTEE_OPINION_OUTPUT = AgentOutputSchema(
    schema_id="committee_opinion",
    required_fields=(
        "member_name",
        "role",
        "symbol",
        "viewpoint",
        "confidence",
        "evidence",
        "risks",
        "catalysts",
    ),
)

CHAIRMAN_SUMMARY_OUTPUT = AgentOutputSchema(
    schema_id="chairman_summary",
    required_fields=(
        "symbol",
        *RECOMMENDATION_FIELDS,
        "rationale",
        "data_confidence",
    ),
)

RESEARCH_ONLY_GUARDRAILS: tuple[str, ...] = (
    "Research only; do not place trades or trigger automatic trading.",
    "Do not request or embed API keys.",
    "Ground conclusions in provided context and memory metadata.",
)

XIXI_PROFILE = AgentProfile(
    agent_id="xixi",
    name="Xixi",
    role=AgentRole.FUNDAMENTAL_ANALYST,
    mandate=(
        "Assess business quality, financial durability, valuation support, "
        "and thesis strength."
    ),
    prompt_source="committee/prompts/xixi.md",
    context_requirement=AgentContextRequirement(
        required_sections=("market", "financials", "valuation", "sec_filings"),
        optional_sections=("macro", "regime", "knowledge_base", "news"),
    ),
    memory_policy=AgentMemoryPolicy(
        memory_scopes=("thesis", "prior_committee_decisions", "known_risks"),
        max_items=6,
    ),
    output_schema=COMMITTEE_OPINION_OUTPUT,
    capabilities=(
        "fundamental_analysis",
        "financial_statement_review",
        "valuation_review",
        "business_quality_assessment",
    ),
    research_guardrails=RESEARCH_ONLY_GUARDRAILS,
)

DONGDONG_PROFILE = AgentProfile(
    agent_id="dongdong",
    name="Dongdong",
    role=AgentRole.OPPORTUNITY_HUNTER,
    mandate=(
        "Identify upside opportunities, catalysts, inflections, momentum, "
        "and favorable asymmetry."
    ),
    prompt_source="committee/prompts/dongdong.md",
    context_requirement=AgentContextRequirement(
        required_sections=("market", "news", "momentum", "sentiment"),
        optional_sections=("sector_rotation", "valuation", "knowledge_base", "macro"),
    ),
    memory_policy=AgentMemoryPolicy(
        memory_scopes=("catalysts", "watchlist_events", "prior_committee_decisions"),
        max_items=6,
    ),
    output_schema=COMMITTEE_OPINION_OUTPUT,
    capabilities=(
        "catalyst_detection",
        "opportunity_screening",
        "momentum_review",
        "sentiment_review",
    ),
    research_guardrails=RESEARCH_ONLY_GUARDRAILS,
)

YOYO_PROFILE = AgentProfile(
    agent_id="yoyo",
    name="Yoyo",
    role=AgentRole.RISK_OFFICER,
    mandate=(
        "Identify downside risks, data quality concerns, adverse scenarios, "
        "and position-sizing constraints."
    ),
    prompt_source="committee/prompts/yoyo.md",
    context_requirement=AgentContextRequirement(
        required_sections=("market", "risk", "health", "data_quality"),
        optional_sections=("portfolio", "sentiment", "sec_filings", "knowledge_base"),
    ),
    memory_policy=AgentMemoryPolicy(
        memory_scopes=("known_risks", "unresolved_debates", "postmortems"),
        max_items=8,
    ),
    output_schema=COMMITTEE_OPINION_OUTPUT,
    capabilities=(
        "risk_assessment",
        "drawdown_review",
        "data_quality_review",
        "scenario_analysis",
    ),
    research_guardrails=RESEARCH_ONLY_GUARDRAILS,
)

CHAIRMAN_PROFILE = AgentProfile(
    agent_id="chairman",
    name="Chairman",
    role=AgentRole.CHAIRMAN,
    mandate="Synthesize committee debate into a final research-only recommendation.",
    prompt_source="committee/prompts/chairman.md",
    context_requirement=AgentContextRequirement(
        required_sections=("committee_opinions", "investment_intelligence"),
        optional_sections=("portfolio", "knowledge_base", "data_quality"),
    ),
    memory_policy=AgentMemoryPolicy(
        memory_scopes=("prior_committee_decisions", "thesis", "unresolved_debates"),
        max_items=10,
    ),
    output_schema=CHAIRMAN_SUMMARY_OUTPUT,
    capabilities=(
        "committee_synthesis",
        "recommendation_review",
        "evidence_weighting",
        "risk_balancing",
    ),
    research_guardrails=(
        *RESEARCH_ONLY_GUARDRAILS,
        (
            "Every recommendation must include action, confidence, horizon, "
            "evidence, risks, and catalysts."
        ),
    ),
)

DEFAULT_AGENT_PROFILES: tuple[AgentProfile, ...] = (
    XIXI_PROFILE,
    DONGDONG_PROFILE,
    YOYO_PROFILE,
    CHAIRMAN_PROFILE,
)
