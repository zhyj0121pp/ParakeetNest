"""Debug inspection helpers for ticker-level committee fact inputs.

Diagnostic summary:
- Currently available in ResearchTickerReport from existing context models:
  price, absolute and percent daily change, volume bucket, market-cap bucket,
  trailing PE, ticker-specific Yahoo news headlines, latest ticker-specific SEC
  filing metadata, macro/regime facts, market_context risk facts, privacy-safe
  portfolio buckets, and source labels.
- Missing from current context boundaries unless a context provider already attaches
  them to market points: sector, industry, forward PE, and beta.
- Future expansion would require provider/model work to carry Yahoo company profile
  fields or additional quote statistics through the context layer.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from parakeetnest.research.models import InvestmentResearchReport, ResearchTickerReport


def inspect_committee_fact_inputs(report: InvestmentResearchReport) -> str:
    """Render per-ticker factual inputs used before committee reasoning."""
    lines: list[str] = [
        f"report: {report.title}",
        f"mode: {report.mode.value}",
        f"generated_at: {report.generated_at.isoformat()}",
        "",
    ]
    for ticker_report in report.ticker_reports:
        lines.extend(_render_ticker_report(ticker_report))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_ticker_report(ticker_report: ResearchTickerReport) -> list[str]:
    return [
        f"ticker: {ticker_report.ticker}",
        *_render_section("public_market_facts", ticker_report.public_market_facts),
        *_render_section("news_facts", ticker_report.news_facts),
        *_render_section("company_facts", ticker_report.company_facts),
        *_render_section("macro_facts", ticker_report.macro_facts),
        *_render_section("market_context_facts", _market_context_facts(ticker_report)),
        *_render_section(
            "position_context",
            _position_context_lines(ticker_report.position_context),
        ),
        *_render_section("source_summaries", ticker_report.source_summaries),
    ]


def _market_context_facts(ticker_report: ResearchTickerReport) -> tuple[str, ...]:
    facts: list[str] = []
    for finding in ticker_report.findings:
        if finding.source == "market_context":
            facts.append(f"market_context: {finding.summary}")
            facts.extend(
                f"market_context evidence: {note}"
                for note in finding.evidence_notes
            )
    for risk in ticker_report.risks:
        if "market_context: factual market context" in risk.evidence_notes:
            facts.append(f"market_context risk: {risk.summary}")
    return _unique(facts)


def _position_context_lines(context: Any | None) -> tuple[str, ...]:
    if context is None:
        return ()
    values = asdict(context) if is_dataclass(context) else dict(vars(context))
    allowed_fields = (
        "ticker",
        "privacy_level",
        "is_holding",
        "position_size_bucket",
        "portfolio_rank_bucket",
        "unrealized_return_bucket",
        "holding_role",
        "add_allowed",
        "trim_candidate",
    )
    return tuple(
        f"{field_name}={values[field_name]}"
        for field_name in allowed_fields
        if field_name in values
    )


def _render_section(title: str, values: tuple[str, ...]) -> list[str]:
    if not values:
        return [f"{title}:", "  - none"]
    return [f"{title}:", *(f"  - {value}" for value in values)]


def _unique(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


__all__ = ["inspect_committee_fact_inputs"]
