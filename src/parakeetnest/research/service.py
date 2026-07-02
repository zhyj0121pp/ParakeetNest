"""Application service for assembling investment research reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol

from parakeetnest.committee.judgment import CommitteeJudgmentService
from parakeetnest.committee.personas import PermanentCommitteeService
from parakeetnest.committee.prompting import (
    ADVISORY_ONLY_DISCLAIMER,
    CommitteePromptBuilder,
    CommitteePromptContext,
    PersonaDrivenCommitteePromptBuilder,
)
from parakeetnest.context.models import (
    ContextRequest,
    PortfolioAllocationContextItem,
    PortfolioPosition,
    PortfolioSnapshot,
)
from parakeetnest.context.provider import ContextProviderResult
from parakeetnest.research.models import (
    InvestmentResearchReport,
    ReportMode,
    ResearchCatalyst,
    ResearchFinding,
    ResearchRisk,
    ResearchTickerReport,
)


class _PortfolioService(Protocol):
    def get_snapshot(self, account_id: str) -> Any:
        """Return a portfolio snapshot for an account."""


class _PortfolioContextProvider(Protocol):
    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        """Return portfolio context for a context-layer request."""


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


class _PermanentCommitteeService(Protocol):
    def daily_investment_committee(self) -> Any:
        """Return the stable daily investment committee."""


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
        portfolio_context_provider: _PortfolioContextProvider | None = None,
        watchlist_service: _WatchlistService | None = None,
        intelligence_service: _IntelligenceService | None = None,
        committee_service: _PermanentCommitteeService | None = None,
        prompt_builder: CommitteePromptBuilder | None = None,
        judgment_service: CommitteeJudgmentService | None = None,
    ) -> None:
        self._portfolio_service = portfolio_service
        self._portfolio_context_provider = portfolio_context_provider
        self._watchlist_service = watchlist_service
        self._intelligence_service = intelligence_service
        self._committee_service = committee_service or PermanentCommitteeService()
        self._prompt_builder = prompt_builder or PersonaDrivenCommitteePromptBuilder()
        self._judgment_service = judgment_service or CommitteeJudgmentService()

    def generate_report(
        self,
        tickers: tuple[str, ...] | list[str],
        *,
        account_id: str | None = None,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
        mode: ReportMode | str = ReportMode.MORNING,
    ) -> InvestmentResearchReport:
        """Generate a research report for the requested tickers."""
        normalized_tickers = _normalize_tickers(tickers)
        if not normalized_tickers:
            raise ValueError("at least one ticker is required")
        report_mode = ReportMode.from_value(mode)

        portfolio_snapshot = self._get_portfolio_snapshot(account_id)
        portfolio_context = self._get_portfolio_context(
            account_id,
            normalized_tickers,
            as_of=generated_at,
            portfolio_snapshot=portfolio_snapshot,
        )
        dependency_notes = _dependency_notes(
            has_portfolio=self._has_portfolio_context(),
            has_watchlist=self._watchlist_service is not None,
            has_intelligence=self._intelligence_service is not None,
        )
        ticker_reports = tuple(
            self._build_ticker_report(
                _TickerInputs(
                    ticker=ticker,
                    holding=_find_holding(
                        portfolio_snapshot or portfolio_context,
                        ticker,
                    ),
                    watchlist_insight=self._get_watchlist_insight(ticker),
                    intelligence_context=self._get_intelligence_context(
                        ticker,
                        as_of_date=as_of_date,
                    ),
                    evidence_notes=dependency_notes,
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
            dependency_notes
            + tuple(
                note
                for ticker_report in ticker_reports
                for note in ticker_report.evidence_notes
            )
        )
        market_summary = _market_summary(ticker_reports)
        portfolio_review = _portfolio_review(
            ticker_reports,
            has_portfolio=self._has_portfolio_context(),
        )
        watchlist_review = _watchlist_review(
            ticker_reports,
            has_watchlist=self._watchlist_service is not None,
        )
        prompt_contexts = _build_committee_prompt_contexts(
            self._committee_service,
            ticker_reports,
            market_summary=market_summary,
            portfolio_review=portfolio_review,
            watchlist_review=watchlist_review,
            evidence_notes=evidence_notes,
        )
        committee_prompts = self._prompt_builder.build_prompts(prompt_contexts)
        return InvestmentResearchReport(
            ticker_reports=ticker_reports,
            mode=report_mode,
            generated_at=generated_at or datetime.now(UTC),
            market_summary=market_summary,
            portfolio_review=portfolio_review,
            watchlist_review=watchlist_review,
            committee_opinions=self._judgment_service.build_opinions(
                committee_prompts,
                ticker_reports,
            ),
            portfolio_context=portfolio_context,
            committee_consensus=self._judgment_service.build_consensus(
                ticker_reports,
            ),
            source_summaries=source_summaries,
            evidence_notes=evidence_notes,
        )

    def _build_ticker_report(self, inputs: _TickerInputs) -> ResearchTickerReport:
        findings = _build_findings(inputs)
        risks = _build_risks(inputs)
        catalysts = _build_catalysts(inputs)
        bull_case = _build_bull_case(inputs)
        bear_case = _build_bear_case(inputs, risks)
        return ResearchTickerReport(
            ticker=inputs.ticker,
            summary=_summary(inputs),
            bull_case=bull_case,
            bear_case=bear_case,
            risks=risks,
            catalysts=catalysts,
            findings=findings,
            source_summaries=_source_summaries(inputs),
            evidence_notes=(),
        )

    def _get_portfolio_snapshot(self, account_id: str | None) -> Any | None:
        if self._portfolio_service is None or account_id is None:
            return None
        return self._portfolio_service.get_snapshot(account_id)

    def _get_portfolio_context(
        self,
        account_id: str | None,
        tickers: tuple[str, ...],
        *,
        as_of: datetime | None,
        portfolio_snapshot: Any | None,
    ) -> PortfolioSnapshot | None:
        if self._portfolio_context_provider is not None and account_id is not None:
            result = self._portfolio_context_provider.build_context(
                ContextRequest(
                    question="Build portfolio context for daily report.",
                    symbols=tickers,
                    as_of=as_of,
                    include_portfolio=True,
                )
            )
            return result.partial_context.portfolio
        if portfolio_snapshot is not None:
            return _portfolio_context_from_snapshot(portfolio_snapshot)
        return None

    def _has_portfolio_context(self) -> bool:
        return (
            self._portfolio_service is not None
            or self._portfolio_context_provider is not None
        )

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
                evidence_notes=(),
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
                    "Current holding value: "
                    f"{_format_money(inputs.holding.market_value)}.",
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
                evidence_notes=(),
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
                summary=(
                    "Portfolio review can decide whether to add, hold, or "
                    "reduce exposure."
                ),
                horizon="next report cycle",
                evidence_notes=("Existing portfolio holding.",),
            )
        )
    if not catalysts:
        catalysts.append(
            ResearchCatalyst(
                summary=(
                    "Add thesis, signals, and portfolio context to strengthen "
                    "evidence."
                ),
                horizon="next research update",
                evidence_notes=(),
            )
        )
    return tuple(catalysts)


def _build_bull_case(inputs: _TickerInputs) -> tuple[str, ...]:
    bull_case: list[str] = []
    if inputs.watchlist_insight is not None:
        bull_case.extend(inputs.watchlist_insight.bullish_factors)
    unrealized_return = _holding_unrealized_return(inputs.holding)
    if unrealized_return is not None and unrealized_return >= 0:
        bull_case.append(
            "Portfolio position is up "
            f"{_format_percent(unrealized_return)}."
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
    unrealized_return = _holding_unrealized_return(inputs.holding)
    if unrealized_return is not None and unrealized_return < 0:
        bear_case.append(
            "Portfolio position is down "
            f"{_format_percent(unrealized_return)}."
        )
    if not bear_case:
        bear_case.extend(risk.summary for risk in risks[:1])
    return _unique(bear_case)


def _summary(inputs: _TickerInputs) -> str:
    if inputs.holding is not None and inputs.watchlist_insight is not None:
        return (
            f"{inputs.ticker} is both a portfolio holding and watchlist "
            "research item."
        )
    if inputs.holding is not None:
        return f"{inputs.ticker} is an existing portfolio holding."
    if inputs.watchlist_insight is not None:
        return inputs.watchlist_insight.summary
    return (
        f"{inputs.ticker} is included for research, but connected context is "
        "limited."
    )


def _holding_summary(holding: Any) -> str:
    symbol = _holding_symbol(holding)
    market_value = getattr(holding, "market_value", None)
    return_percent = getattr(holding, "unrealized_gain_loss_percent", None)
    if return_percent is None:
        return (
            f"{symbol} position value is {_format_money(market_value)} "
            "with unrealized return unknown."
        )
    return (
        f"{symbol} position value is {_format_money(market_value)} "
        f"with unrealized return {_format_percent(return_percent)}."
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


def _market_summary(ticker_reports: tuple[ResearchTickerReport, ...]) -> str:
    ticker_count = len(ticker_reports)
    if ticker_count == 1:
        return (
            "Market summary covers 1 requested ticker using connected research "
            "context."
        )
    return (
        f"Market summary covers {ticker_count} requested tickers using connected "
        "research context."
    )


def _portfolio_review(
    ticker_reports: tuple[ResearchTickerReport, ...],
    *,
    has_portfolio: bool,
) -> str:
    if not has_portfolio:
        return (
            "No portfolio service is connected; review remains advisory and "
            "context-limited."
        )
    holding_count = sum(
        any(finding.source == "portfolio" for finding in ticker_report.findings)
        for ticker_report in ticker_reports
    )
    return f"Portfolio review found {holding_count} covered holding(s)."


def _watchlist_review(
    ticker_reports: tuple[ResearchTickerReport, ...],
    *,
    has_watchlist: bool,
) -> str:
    if not has_watchlist:
        return (
            "No watchlist service is connected; watchlist review uses requested "
            "tickers only."
        )
    watchlist_count = sum(
        any(finding.source == "watchlist" for finding in ticker_report.findings)
        for ticker_report in ticker_reports
    )
    return f"Watchlist review found {watchlist_count} covered watchlist item(s)."


def _build_committee_prompt_contexts(
    committee_service: _PermanentCommitteeService,
    ticker_reports: tuple[ResearchTickerReport, ...],
    *,
    market_summary: str,
    portfolio_review: str,
    watchlist_review: str,
    evidence_notes: tuple[str, ...],
) -> tuple[CommitteePromptContext, ...]:
    tickers = tuple(ticker_report.ticker for ticker_report in ticker_reports)
    ticker_summaries = tuple(
        f"{ticker_report.ticker}: {ticker_report.summary}"
        for ticker_report in ticker_reports
    )
    key_risks = _unique(
        f"{ticker_report.ticker}: {risk.summary}"
        for ticker_report in ticker_reports
        for risk in ticker_report.risks
    )
    upcoming_catalysts = _unique(
        f"{ticker_report.ticker}: {catalyst.summary}"
        for ticker_report in ticker_reports
        for catalyst in ticker_report.catalysts
    )
    return tuple(
        CommitteePromptContext(
            persona=member.persona,
            tickers=tickers,
            market_summary=market_summary,
            portfolio_review=portfolio_review,
            watchlist_review=watchlist_review,
            ticker_summaries=ticker_summaries,
            evidence_notes=evidence_notes,
            key_risks=key_risks,
            upcoming_catalysts=upcoming_catalysts,
            advisory_only_disclaimer=ADVISORY_ONLY_DISCLAIMER,
        )
        for member in committee_service.daily_investment_committee()
    )


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
    holdings = getattr(portfolio_snapshot, "holdings", ()) or getattr(
        portfolio_snapshot,
        "positions",
        (),
    )
    for holding in holdings:
        if _holding_symbol(holding) == ticker:
            return holding
    return None


def _holding_symbol(holding: Any) -> str:
    return str(getattr(holding, "symbol", getattr(holding, "ticker", ""))).upper()


def _holding_unrealized_return(holding: Any | None) -> float | None:
    if holding is None:
        return None
    value = getattr(holding, "unrealized_gain_loss_percent", None)
    if value is not None:
        return float(value)
    unrealized_pl = getattr(holding, "unrealized_pl", None)
    cost_basis = getattr(holding, "cost_basis", None)
    if unrealized_pl is None or cost_basis in (None, 0):
        return None
    return float(unrealized_pl) / float(cost_basis)


def _portfolio_context_from_snapshot(snapshot: Any) -> PortfolioSnapshot:
    total_equity = getattr(snapshot, "total_equity", None)
    total_market_value = getattr(snapshot, "total_market_value", None)
    total_cash = getattr(snapshot, "total_cash", None)
    holdings = tuple(getattr(snapshot, "holdings", ()))
    positions = tuple(
        PortfolioPosition(
            symbol=_holding_symbol(holding),
            quantity=float(getattr(holding, "quantity", 0.0)),
            name=getattr(holding, "name", None),
            market_value=getattr(holding, "market_value", None),
            cost_basis=_holding_cost_basis(holding),
            unrealized_pl=getattr(holding, "unrealized_gain_loss", None),
            weight=_holding_weight(holding, total_equity),
            sector=getattr(holding, "sector", None),
        )
        for holding in holdings
    )
    return PortfolioSnapshot(
        source="portfolio_service",
        fetched_at=getattr(snapshot, "as_of", None),
        account_id=getattr(snapshot, "account_id", None),
        total_equity=total_equity,
        total_market_value=total_market_value,
        total_cash=total_cash,
        holding_count=len(positions),
        symbols=tuple(position.symbol for position in positions),
        allocation_by_symbol=tuple(
            PortfolioAllocationContextItem(
                category=position.symbol,
                value=float(position.market_value or 0.0),
                percent=float(position.weight or 0.0),
            )
            for position in positions
        ),
        positions=positions,
        cash_balance=total_cash,
        total_value=total_equity,
    )


def _holding_cost_basis(holding: Any) -> float | None:
    quantity = getattr(holding, "quantity", None)
    average_cost = getattr(holding, "average_cost", None)
    if quantity is None or average_cost is None:
        return None
    return float(quantity) * float(average_cost)


def _holding_weight(holding: Any, total_equity: float | None) -> float | None:
    if total_equity is None or float(total_equity) == 0:
        return None
    market_value = getattr(holding, "market_value", None)
    if market_value is None:
        return None
    return float(market_value) / float(total_equity)


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
