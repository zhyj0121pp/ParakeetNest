"""Portfolio committee agent profile definitions.

These profiles describe read-only advisory portfolio specialists. They do not
execute trades, connect to brokerages, persist data, or orchestrate meetings.
"""

from __future__ import annotations

from parakeetnest.committee.agent_profiles import (
    AgentContextRequirement,
    AgentMemoryPolicy,
    AgentOutputSchema,
    AgentProfile,
    AgentRegistry,
    AgentRole,
)


PORTFOLIO_COMMITTEE_OUTPUT = AgentOutputSchema(
    schema_id="portfolio_committee_observation",
    required_fields=(
        "agent_name",
        "role",
        "portfolio_view",
        "advisory_action",
        "confidence",
        "horizon",
        "evidence",
        "risks",
        "catalysts",
    ),
)

PORTFOLIO_ADVISORY_GUARDRAILS: tuple[str, ...] = (
    "Advisory research only; do not trigger automatic trading.",
    "Use only provided portfolio, market, macro, investment intelligence, and memory context.",
    "Discuss uncertainties and data gaps before drawing portfolio conclusions.",
    "Avoid guarantees, promises of returns, or personalized financial advice.",
)

PORTFOLIO_CONTEXT_SECTIONS: tuple[str, ...] = (
    "portfolio",
    "market",
    "macro",
    "investment_intelligence",
)

PORTFOLIO_MEMORY_SCOPES: tuple[str, ...] = (
    "prior_committee_decisions",
    "known_risks",
    "unresolved_debates",
)

PORTFOLIO_MANAGER_PROFILE = AgentProfile(
    agent_id="portfolio_manager",
    name="Portfolio Manager",
    role=AgentRole.PORTFOLIO_MANAGER,
    mandate=(
        "Assess overall portfolio construction using portfolio context when "
        "available, including total equity, top holdings, position sizing, "
        "sector allocation, risk summary, concentration, and portfolio-level "
        "tradeoffs."
    ),
    prompt_source="committee/prompts/portfolio_manager.md",
    context_requirement=AgentContextRequirement(
        required_sections=("portfolio",),
        optional_sections=PORTFOLIO_CONTEXT_SECTIONS[1:],
    ),
    memory_policy=AgentMemoryPolicy(
        memory_scopes=PORTFOLIO_MEMORY_SCOPES,
        max_items=8,
    ),
    output_schema=PORTFOLIO_COMMITTEE_OUTPUT,
    capabilities=(
        "portfolio_construction_review",
        "position_sizing_observations",
        "concentration_observations",
        "portfolio_tradeoff_discussion",
    ),
    research_guardrails=PORTFOLIO_ADVISORY_GUARDRAILS,
)

PORTFOLIO_RISK_MANAGER_PROFILE = AgentProfile(
    agent_id="portfolio_risk_manager",
    name="Risk Manager",
    role=AgentRole.PORTFOLIO_RISK_MANAGER,
    mandate=(
        "Assess downside risk using portfolio context when available, including "
        "total equity, top holdings, sector allocation, concentration risk, "
        "cash buffer, exposure imbalance, risk summary, and drawdown awareness."
    ),
    prompt_source="committee/prompts/portfolio_risk_manager.md",
    context_requirement=AgentContextRequirement(
        required_sections=("portfolio",),
        optional_sections=PORTFOLIO_CONTEXT_SECTIONS[1:],
    ),
    memory_policy=AgentMemoryPolicy(
        memory_scopes=("known_risks", "postmortems", "unresolved_debates"),
        max_items=10,
    ),
    output_schema=PORTFOLIO_COMMITTEE_OUTPUT,
    capabilities=(
        "downside_risk_review",
        "concentration_risk_review",
        "cash_buffer_review",
        "exposure_imbalance_review",
        "drawdown_awareness",
    ),
    research_guardrails=PORTFOLIO_ADVISORY_GUARDRAILS,
)

SECTOR_ANALYST_PROFILE = AgentProfile(
    agent_id="sector_analyst",
    name="Sector Analyst",
    role=AgentRole.SECTOR_ANALYST,
    mandate=(
        "Assess sector and industry exposure using portfolio context when "
        "available, including total equity, top holdings, sector allocation, "
        "risk summary, over or under concentration, and thematic exposure."
    ),
    prompt_source="committee/prompts/sector_analyst.md",
    context_requirement=AgentContextRequirement(
        required_sections=("portfolio",),
        optional_sections=(
            "sector_rotation",
            "market",
            "macro",
            "investment_intelligence",
        ),
    ),
    memory_policy=AgentMemoryPolicy(
        memory_scopes=("sector_views", "catalysts", "prior_committee_decisions"),
        max_items=8,
    ),
    output_schema=PORTFOLIO_COMMITTEE_OUTPUT,
    capabilities=(
        "sector_allocation_review",
        "industry_exposure_review",
        "over_under_concentration_review",
        "thematic_exposure_review",
    ),
    research_guardrails=PORTFOLIO_ADVISORY_GUARDRAILS,
)

MACRO_STRATEGIST_PROFILE = AgentProfile(
    agent_id="macro_strategist",
    name="Macro Strategist",
    role=AgentRole.MACRO_STRATEGIST,
    mandate=(
        "Assess macro regime fit using portfolio context when available, "
        "including total equity, top holdings, sector allocation, risk summary, "
        "rate sensitivity, liquidity environment, risk-on or risk-off "
        "positioning, and relevant market or macro context."
    ),
    prompt_source="committee/prompts/macro_strategist.md",
    context_requirement=AgentContextRequirement(
        required_sections=("portfolio",),
        optional_sections=(
            "macro",
            "regime",
            "market",
            "sector_rotation",
            "investment_intelligence",
        ),
    ),
    memory_policy=AgentMemoryPolicy(
        memory_scopes=("macro_regime", "known_risks", "prior_committee_decisions"),
        max_items=8,
    ),
    output_schema=PORTFOLIO_COMMITTEE_OUTPUT,
    capabilities=(
        "macro_regime_fit_review",
        "rate_sensitivity_review",
        "liquidity_environment_review",
        "risk_on_risk_off_positioning",
    ),
    research_guardrails=PORTFOLIO_ADVISORY_GUARDRAILS,
)

PORTFOLIO_COMMITTEE_AGENT_PROFILES: tuple[AgentProfile, ...] = (
    PORTFOLIO_MANAGER_PROFILE,
    PORTFOLIO_RISK_MANAGER_PROFILE,
    SECTOR_ANALYST_PROFILE,
    MACRO_STRATEGIST_PROFILE,
)


def register_portfolio_committee_agents(
    registry: AgentRegistry,
) -> tuple[AgentProfile, ...]:
    """Register portfolio committee agent profiles in deterministic order."""
    for profile in PORTFOLIO_COMMITTEE_AGENT_PROFILES:
        registry.register(profile)
    return PORTFOLIO_COMMITTEE_AGENT_PROFILES


__all__ = [
    "MACRO_STRATEGIST_PROFILE",
    "PORTFOLIO_ADVISORY_GUARDRAILS",
    "PORTFOLIO_COMMITTEE_AGENT_PROFILES",
    "PORTFOLIO_COMMITTEE_OUTPUT",
    "PORTFOLIO_MANAGER_PROFILE",
    "PORTFOLIO_RISK_MANAGER_PROFILE",
    "SECTOR_ANALYST_PROFILE",
    "register_portfolio_committee_agents",
]
