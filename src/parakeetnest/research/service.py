"""Application service for assembling investment research reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol

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


class _PortfolioService(Protocol):
    def get_snapshot(self, account_id: str) -> Any:
        """Return a portfolio snapshot for an account."""


class _WatchlistService(Protocol):
    def build_insight(self, symbol: str) -> Any:
        """Return watchlist insight for a symbol."""


class _IntelligenceService(Protocol):
    def build_context(
        self,
        *,
        as_of_date: date | None = None,
        universe: str = "US",
        symbol: str = "SPY",
    ) -> Any:
        """Return investment intelligence context for a symbol."""


@dataclass(frozen=True)
class _TickerInputs:
    ticker: str
    holding: Any | None = None
    watchlist_insight: Any | None = None
    intelligence_context: Any | None = None
    evidence_notes: tuple[str, ...] = ()


class InvestmentResearchService:
    """Generate provider-neutral research reports from existing abstractions."""

    def __init__(
        self,
        *,
        portfolio_service: _PortfolioService | None = None,
        watchlist_service: _WatchlistService | None = None,
        intelligence_service: _IntelligenceService | None = None,
        default_horizon: str = "3-6 months",
    ) -> None:
        self._portfolio_service = portfolio_service
        self._watchlist_service = watchlist_service
        self._intelligence_service = intelligence_service
        self._default_horizon = default_horizon

    def generate_report(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
    ) -> InvestmentResearchReport:
        """Generate a research report for the requested tickers."""
        normalized_tickers = _normalize_tickers(tickers)
        if not normalized_tickers:
            raise ValueError("at least one ticker is required")

        portfolio_snapshot = self._get_portfolio_snapshot(account_id)
        ticker_reports = tuple(
            self._build_ticker_report(
                _TickerInputs(
                    ticker=ticker,
                    holding=_find_holding(portfolio_snapshot, ticker),
                    watchlist_insight=self._get_watchlist_insight(ticker),
                    intelligence_context=self._get_intelligence_context(
                        ticker,
                        as_of_date=as_of_date,
                    ),
                    evidence_notes=_dependency_notes(
                        has_portfolio=self._portfolio_service is not None,
                        has_watchlist=self._watchlist_service is not None,
                        has_intelligence=self._intelligence_service is not None,
                    ),
                )
            )
            for ticker in normalized_tickers
        )
        source_summaries = _unique(
            summary
            for ticker_report in ticker_reports
            for summary in ticker_report.source_summaries
        )
        evidence_notes = _unique(
            note
            for ticker_report in ticker_reports
            for note in ticker_report.evidence_notes
        )
        return InvestmentResearchReport(
            ticker_reports=ticker_reports,
            generated_at=generated_at or datetime.now(UTC),
            source_summaries=source_summaries,
            evidence_notes=evidence_notes,
        )

    def _build_ticker_report(self, inputs: _TickerInputs) -> ResearchTickerReport:
        findings = _build_findings(inputs)
        risks = _build_risks(inputs)
        catalysts = _build_catalysts(inputs)
        bull_case = _build_bull_case(inputs)
        bear_case = _build_bear_case(inputs, risks)
        evidence = _unique(finding.summary for finding in findings)
        recommendation = ResearchRecommendation(
            action=_recommendation_action(inputs),
            confidence=_confidence(inputs),
            horizon=self._default_horizon,
            evidence=evidence
            or (f"{inputs.ticker} included in requested research list.",),
            risks=tuple(risk.summary for risk in risks),
            catalysts=tuple(catalyst.summary for catalyst in catalysts),
            rationale=_recommendation_rationale(inputs),
        )
        return ResearchTickerReport(
            ticker=inputs.ticker,
            summary=_summary(inputs),
            bull_case=bull_case,
            bear_case=bear_case,
            risks=risks,
            catalysts=catalysts,
            recommendation=recommendation,
            findings=findings,
            source_summaries=_source_summaries(inputs),
            evidence_notes=inputs.evidence_notes,
        )

    def _get_portfolio_snapshot(self, account_id: str | None) -> Any | None:
        if self._portfolio_service is None or account_id is None:
            return None
        return self._portfolio_service.get_snapshot(account_id)

    def _get_watchlist_insight(self, ticker: str) -> Any | None:
        if self._watchlist_service is None:
            return None
        try:
            return self._watchlist_service.build_insight(ticker)
        except ValueError:
            return None

    def _get_intelligence_context(
        self,
        ticker: str,
        *,
        as_of_date: date | None,
    ) -> Any | None:
        if self._intelligence_service is None:
            return None
        return self._intelligence_service.build_context(
            as_of_date=as_of_date,
            symbol=ticker,
        )


def _build_findings(inputs: _TickerInputs) -> tuple[ResearchFinding, ...]:
    findings: list[ResearchFinding] = []
    if inputs.holding is not None:
        findings.append(
            ResearchFinding(
                summary=_holding_summary(inputs.holding),
                source="portfolio",
                evidence_notes=("Existing portfolio holding.",),
            )
        )
    if inputs.watchlist_insight is not None:
        findings.append(
            ResearchFinding(
                summary=inputs.watchlist_insight.summary,
                source="watchlist",
                evidence_notes=_unique(
                    tuple(inputs.watchlist_insight.bullish_factors)
                    + tuple(inputs.watchlist_insight.bearish_factors)
                    + tuple(inputs.watchlist_insight.open_questions)
                ),
            )
        )
    if inputs.intelligence_context is not None:
        findings.append(
            ResearchFinding(
                summary=_intelligence_summary(inputs.intelligence_context),
                source="investment_intelligence",
                evidence_notes=_intelligence_evidence(inputs.intelligence_context),
            )
        )
    if not findings:
        findings.append(
            ResearchFinding(
                summary=(
                    f"{inputs.ticker} has no connected portfolio, watchlist, "
                    "or intelligence context yet."
                ),
                source="research_service",
                evidence_notes=inputs.evidence_notes,
            )
        )
    return tuple(findings)


def _build_risks(inputs: _TickerInputs) -> tuple[ResearchRisk, ...]:
    risks: list[ResearchRisk] = []
    if inputs.watchlist_insight is not None:
        risks.extend(
            ResearchRisk(summary=factor, evidence_notes=("Watchlist bear case.",))
            for factor in inputs.watchlist_insight.bearish_factors
        )
    if inputs.holding is not None:
        risks.append(
            ResearchRisk(
                summary=(
                    "Position sizing and portfolio concentration should be "
                    "reviewed before adding exposure."
                ),
                evidence_notes=(
                    f"Current holding value: {_format_money(inputs.holding.market_value)}.",
                ),
            )
        )
    risk_summary = _risk_summary(inputs.intelligence_context)
    if risk_summary is not None:
        risks.append(
            ResearchRisk(
                summary=risk_summary,
                evidence_notes=("Aggregate intelligence context.",),
            )
        )
    if not risks:
        risks.append(
            ResearchRisk(
                summary="Insufficient connected research context is the primary risk.",
                evidence_notes=inputs.evidence_notes,
            )
        )
    return tuple(risks)


def _build_catalysts(inputs: _TickerInputs) -> tuple[ResearchCatalyst, ...]:
    catalysts: list[ResearchCatalyst] = []
    if inputs.watchlist_insight is not None:
        catalysts.extend(
            ResearchCatalyst(
                summary=factor,
                horizon="watchlist horizon",
                evidence_notes=("Watchlist bull case.",),
            )
            for factor in inputs.watchlist_insight.bullish_factors
        )
    if inputs.holding is not None:
        catalysts.append(
            ResearchCatalyst(
                summary="Portfolio review can decide whether to add, hold, or reduce exposure.",
                horizon="next report cycle",
                evidence_notes=("Existing portfolio holding.",),
            )
        )
    if not catalysts:
        catalysts.append(
            ResearchCatalyst(
                summary="Add thesis, signals, and portfolio context to upgrade the recommendation.",
                horizon="next research update",
                evidence_notes=inputs.evidence_notes,
            )
        )
    return tuple(catalysts)


def _build_bull_case(inputs: _TickerInputs) -> tuple[str, ...]:
    bull_case: list[str] = []
    if inputs.watchlist_insight is not None:
        bull_case.extend(inputs.watchlist_insight.bullish_factors)
    if (
        inputs.holding is not None
        and inputs.holding.unrealized_gain_loss_percent >= 0
    ):
        bull_case.append(
            "Portfolio position is up "
            f"{_format_percent(inputs.holding.unrealized_gain_loss_percent)}."
        )
    if not bull_case:
        bull_case.append("No connected bull-case evidence yet.")
    return _unique(bull_case)


def _build_bear_case(
    inputs: _TickerInputs,
    risks: tuple[ResearchRisk, ...],
) -> tuple[str, ...]:
    bear_case: list[str] = []
    if inputs.watchlist_insight is not None:
        bear_case.extend(inputs.watchlist_insight.bearish_factors)
    if inputs.holding is not None and inputs.holding.unrealized_gain_loss_percent < 0:
        bear_case.append(
            "Portfolio position is down "
            f"{_format_percent(inputs.holding.unrealized_gain_loss_percent)}."
        )
    if not bear_case:
        bear_case.extend(risk.summary for risk in risks[:1])
    return _unique(bear_case)


def _summary(inputs: _TickerInputs) -> str:
    if inputs.holding is not None and inputs.watchlist_insight is not None:
        return f"{inputs.ticker} is both a portfolio holding and watchlist research item."
    if inputs.holding is not None:
        return f"{inputs.ticker} is an existing portfolio holding."
    if inputs.watchlist_insight is not None:
        return inputs.watchlist_insight.summary
    return f"{inputs.ticker} is included for research, but connected context is limited."


def _recommendation_action(inputs: _TickerInputs) -> RecommendationType:
    if inputs.watchlist_insight is not None and inputs.holding is None:
        return RecommendationType.WATCH
    if inputs.holding is not None:
        risk_summary = _risk_summary(inputs.intelligence_context) or ""
        if "high" in risk_summary.lower() or "extreme" in risk_summary.lower():
            return RecommendationType.REDUCE
        return RecommendationType.HOLD
    return RecommendationType.WATCH


def _confidence(inputs: _TickerInputs) -> ConfidenceLevel:
    source_count = sum(
        value is not None
        for value in (
            inputs.holding,
            inputs.watchlist_insight,
            inputs.intelligence_context,
        )
    )
    if source_count >= 3:
        return ConfidenceLevel.HIGH
    if source_count == 2:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _recommendation_rationale(inputs: _TickerInputs) -> str:
    if inputs.holding is not None and inputs.watchlist_insight is not None:
        return "Hold until watchlist research produces a stronger add or reduce signal."
    if inputs.holding is not None:
        return "Maintain exposure while evidence base is incomplete."
    return "Monitor until portfolio-grade evidence is available."


def _holding_summary(holding: Any) -> str:
    return (
        f"{holding.symbol} position value is {_format_money(holding.market_value)} "
        f"with unrealized return {_format_percent(holding.unrealized_gain_loss_percent)}."
    )


def _intelligence_summary(context: Any) -> str:
    risk_summary = _risk_summary(context)
    if risk_summary is not None:
        return f"Market intelligence context available: {risk_summary}"
    return "Market intelligence context available for the ticker."


def _intelligence_evidence(context: Any) -> tuple[str, ...]:
    evidence: list[str] = []
    risk = getattr(context, "risk", None)
    if risk is not None:
        if getattr(risk, "summary", None):
            evidence.append(risk.summary)
        if getattr(risk, "overall_level", None):
            evidence.append(f"Risk level: {risk.overall_level.value}.")
    return _unique(evidence) or ("Investment intelligence context generated.",)


def _risk_summary(context: Any | None) -> str | None:
    if context is None:
        return None
    risk = getattr(context, "risk", None)
    if risk is None:
        return None
    if getattr(risk, "summary", None):
        return risk.summary
    level = getattr(risk, "overall_level", None)
    score = getattr(risk, "overall_score", None)
    if level is not None and score is not None:
        return f"Aggregate risk is {level.value} ({score:.2f})."
    return None


def _source_summaries(inputs: _TickerInputs) -> tuple[str, ...]:
    summaries: list[str] = []
    if inputs.holding is not None:
        summaries.append("portfolio: current holding context")
    if inputs.watchlist_insight is not None:
        summaries.append("watchlist: thesis, factors, and open questions")
    if inputs.intelligence_context is not None:
        summaries.append("investment_intelligence: aggregate market context")
    if not summaries:
        summaries.append("research_service: requested ticker only")
    return tuple(summaries)


def _get_ticker(value: str) -> str:
    ticker = str(value).strip().upper()
    if not ticker:
        raise ValueError("ticker is required")
    return ticker


def _normalize_tickers(tickers: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return _unique(_get_ticker(ticker) for ticker in tickers)


def _find_holding(portfolio_snapshot: Any | None, ticker: str) -> Any | None:
    if portfolio_snapshot is None:
        return None
    for holding in portfolio_snapshot.holdings:
        if holding.symbol == ticker:
            return holding
    return None


def _dependency_notes(
    *,
    has_portfolio: bool,
    has_watchlist: bool,
    has_intelligence: bool,
) -> tuple[str, ...]:
    notes = []
    if not has_portfolio:
        notes.append("No portfolio service connected.")
    if not has_watchlist:
        notes.append("No watchlist service connected.")
    if not has_intelligence:
        notes.append("No intelligence service connected.")
    return tuple(notes)


def _format_money(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"${float(value):,.2f}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{float(value) * 100:.1f}%"


def _unique(values: Any) -> tuple[Any, ...]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)


__all__ = ["InvestmentResearchService"]
