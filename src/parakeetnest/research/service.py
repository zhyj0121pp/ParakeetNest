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
    MeetingContext,
    PortfolioAllocationContextItem,
    PortfolioPosition,
    PortfolioSnapshot,
)
from parakeetnest.context.provider import ContextProviderResult
from parakeetnest.portfolio.privacy import (
    PortfolioPositionContext,
    PortfolioPrivacyContextBuilder,
    PortfolioSummary,
)
from parakeetnest.research.models import (
    InvestmentResearchReport,
    ReportMode,
    ResearchCatalyst,
    ResearchFinding,
    ResearchPositionDecision,
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


class _ContextService(Protocol):
    def build_context(self, request: ContextRequest) -> MeetingContext:
        """Return assembled public context for requested symbols."""


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
    portfolio_summary: PortfolioSummary | None = None
    position_context: PortfolioPositionContext | None = None
    public_market_facts: tuple[str, ...] = ()
    profile_facts: tuple[str, ...] = ()
    valuation_facts: tuple[str, ...] = ()
    news_facts: tuple[str, ...] = ()
    company_facts: tuple[str, ...] = ()
    macro_facts: tuple[str, ...] = ()
    evidence_notes: tuple[str, ...] = ()


class InvestmentResearchService:
    """Generate provider-neutral research reports from existing abstractions."""

    def __init__(
        self,
        *,
        portfolio_service: _PortfolioService | None = None,
        portfolio_context_provider: _PortfolioContextProvider | None = None,
        public_context_service: _ContextService | None = None,
        watchlist_service: _WatchlistService | None = None,
        intelligence_service: _IntelligenceService | None = None,
        committee_service: _PermanentCommitteeService | None = None,
        prompt_builder: CommitteePromptBuilder | None = None,
        judgment_service: CommitteeJudgmentService | None = None,
    ) -> None:
        self._portfolio_service = portfolio_service
        self._portfolio_context_provider = portfolio_context_provider
        self._public_context_service = public_context_service
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
        public_context = self._get_public_context(
            normalized_tickers,
            as_of=generated_at,
        )
        privacy_summary, privacy_positions = PortfolioPrivacyContextBuilder().build(
            portfolio_snapshot or portfolio_context,
            normalized_tickers,
        )
        privacy_by_ticker = {
            position_context.ticker: position_context
            for position_context in privacy_positions
        }
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
                    portfolio_summary=privacy_summary,
                    position_context=privacy_by_ticker.get(ticker),
                    public_market_facts=_public_market_facts(public_context, ticker),
                    profile_facts=_profile_facts(public_context, ticker),
                    valuation_facts=_valuation_facts(public_context, ticker),
                    news_facts=_news_facts(public_context, ticker),
                    company_facts=_company_facts(public_context, ticker),
                    macro_facts=_macro_facts(public_context),
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
        position_committee_reviews = tuple(
            self._build_position_committee_review(
                ticker_report,
                dependency_notes=dependency_notes,
            )
            for ticker_report in ticker_reports
        )
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
                language=prompt_contexts[0].report_language if prompt_contexts else None,
            ),
            position_committee_reviews=position_committee_reviews,
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
            portfolio_summary=inputs.portfolio_summary,
            position_context=inputs.position_context,
            public_market_facts=inputs.public_market_facts,
            profile_facts=inputs.profile_facts,
            valuation_facts=inputs.valuation_facts,
            news_facts=inputs.news_facts,
            company_facts=inputs.company_facts,
            macro_facts=inputs.macro_facts,
        )

    def _build_position_committee_review(
        self,
        ticker_report: ResearchTickerReport,
        *,
        dependency_notes: tuple[str, ...],
    ) -> ResearchPositionDecision:
        ticker_reports = (ticker_report,)
        market_summary = _market_summary(ticker_reports)
        portfolio_review = _portfolio_review(
            ticker_reports,
            has_portfolio=self._has_portfolio_context(),
        )
        watchlist_review = _watchlist_review(
            ticker_reports,
            has_watchlist=self._watchlist_service is not None,
        )
        evidence_notes = _unique(dependency_notes + ticker_report.evidence_notes)
        prompt_contexts = _build_committee_prompt_contexts(
            self._committee_service,
            ticker_reports,
            market_summary=market_summary,
            portfolio_review=portfolio_review,
            watchlist_review=watchlist_review,
            evidence_notes=evidence_notes,
        )
        committee_prompts = self._prompt_builder.build_prompts(prompt_contexts)
        opinions = self._judgment_service.build_opinions(
            committee_prompts,
            ticker_reports,
        )
        consensus = self._judgment_service.build_consensus(
            ticker_reports,
            language=prompt_contexts[0].report_language if prompt_contexts else None,
        )
        return ResearchPositionDecision(
            ticker=ticker_report.ticker,
            dongdong_opinion=_opinion_text(opinions, "dongdong"),
            xixi_opinion=_opinion_text(opinions, "xixi"),
            youyou_opinion=_opinion_text(opinions, "youyou"),
            consensus=consensus,
            recommendation=consensus.final_action,
            confidence=consensus.confidence,
            rationale=consensus.rationale,
            evidence=_ticker_evidence(ticker_report),
        )

    def _get_portfolio_snapshot(self, account_id: str | None) -> Any | None:
        if (
            self._portfolio_context_provider is not None
            or self._portfolio_service is None
            or account_id is None
        ):
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

    def _get_public_context(
        self,
        tickers: tuple[str, ...],
        *,
        as_of: datetime | None,
    ) -> MeetingContext | None:
        if self._public_context_service is None:
            return None
        try:
            return self._public_context_service.build_context(
                ContextRequest(
                    question="Build public factual context for daily report.",
                    symbols=tickers,
                    as_of=as_of,
                    include_portfolio=False,
                    include_macro=True,
                    include_knowledge_base=False,
                )
            )
        except Exception:
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
                summary=_portfolio_position_summary(inputs),
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
                summary=_market_context_summary(inputs.intelligence_context),
                source="market_context",
                evidence_notes=_market_context_evidence(inputs.intelligence_context),
            )
        )
    if not findings:
        findings.append(
            ResearchFinding(
                summary="No connected factual context available.",
                source="research_service",
                evidence_notes=(),
            )
        )
    return tuple(findings)


def _build_risks(inputs: _TickerInputs) -> tuple[ResearchRisk, ...]:
    risks: list[ResearchRisk] = []
    if inputs.watchlist_insight is not None:
        risks.extend(
            ResearchRisk(
                summary=factor,
                evidence_notes=("Watchlist user thesis and notes.",),
            )
            for factor in inputs.watchlist_insight.bearish_factors
        )
    if inputs.holding is not None:
        risks.append(
            ResearchRisk(
                summary=_portfolio_position_summary(inputs),
                evidence_notes=("Existing portfolio holding.",),
            )
        )
    risk_facts = _market_context_risk_facts(inputs.intelligence_context)
    if risk_facts:
        risks.append(
            ResearchRisk(
                summary="; ".join(risk_facts),
                evidence_notes=("market_context: factual market context",),
            )
        )
    if not risks:
        risks.append(
            ResearchRisk(
                summary="No connected factual context available.",
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
                evidence_notes=("Watchlist user thesis and notes.",),
            )
            for factor in inputs.watchlist_insight.bullish_factors
        )
    if not catalysts:
        catalysts.append(
            ResearchCatalyst(
                summary="No connected factual context available.",
                horizon=None,
                evidence_notes=(),
            )
        )
    return tuple(catalysts)


def _build_bull_case(inputs: _TickerInputs) -> tuple[str, ...]:
    bull_case: list[str] = []
    if inputs.watchlist_insight is not None:
        bull_case.extend(inputs.watchlist_insight.bullish_factors)
    unrealized_return = _holding_unrealized_return(inputs.holding)
    if unrealized_return is not None and inputs.position_context is not None:
        bull_case.append(
            "Portfolio unrealized return bucket: "
            f"{inputs.position_context.unrealized_return_bucket}."
        )
    if not bull_case:
        bull_case.append("No connected factual context available.")
    return _unique(bull_case)


def _build_bear_case(
    inputs: _TickerInputs,
    risks: tuple[ResearchRisk, ...],
) -> tuple[str, ...]:
    bear_case: list[str] = []
    if inputs.watchlist_insight is not None:
        bear_case.extend(inputs.watchlist_insight.bearish_factors)
    unrealized_return = _holding_unrealized_return(inputs.holding)
    if unrealized_return is not None and inputs.position_context is not None:
        bear_case.append(
            "Portfolio unrealized return bucket: "
            f"{inputs.position_context.unrealized_return_bucket}."
        )
    if not bear_case:
        bear_case.append("No connected factual context available.")
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


def _portfolio_position_summary(inputs: _TickerInputs) -> str:
    context = inputs.position_context
    if context is None:
        return f"{inputs.ticker} is a current portfolio holding."
    return (
        f"{inputs.ticker} portfolio context: "
        f"position size bucket={context.position_size_bucket}; "
        f"rank bucket={context.portfolio_rank_bucket}; "
        f"return bucket={context.unrealized_return_bucket}; "
        f"holding role={context.holding_role}; "
        f"add allowed={context.add_allowed}; "
        f"trim candidate={context.trim_candidate}; "
        f"privacy level={context.privacy_level}."
    )


def _market_context_summary(context: Any) -> str:
    facts = _market_context_risk_facts(context)
    if facts:
        return "Market context facts: " + "; ".join(facts)
    return "Market context facts available."


def _market_context_evidence(context: Any) -> tuple[str, ...]:
    evidence: list[str] = []
    generated_at = getattr(context, "generated_at", None)
    if generated_at is not None:
        evidence.append(f"Generated at: {generated_at}.")
    risk = getattr(context, "risk", None)
    if risk is not None:
        if getattr(risk, "source", None):
            evidence.append(f"Source: {risk.source}.")
        if getattr(risk, "overall_level", None):
            evidence.append(f"Risk level: {risk.overall_level.value}.")
        if getattr(risk, "overall_score", None) is not None:
            evidence.append(f"Risk score: {risk.overall_score:.2f}.")
        for signal in getattr(risk, "signals", ())[:3]:
            evidence.append(
                "Risk signal: "
                f"{signal.label}; category={signal.category.value}; "
                f"level={signal.level.value}; score={signal.score:.2f}."
            )
            metadata = getattr(signal, "metadata", {})
            for key in ("volatility", "drawdown"):
                value = metadata.get(key)
                if value is not None:
                    evidence.append(f"{key.title()}: {value}.")
    return _unique(evidence) or ("market_context: factual market context",)


def _market_context_risk_facts(context: Any | None) -> tuple[str, ...]:
    if context is None:
        return ()
    risk = getattr(context, "risk", None)
    if risk is None:
        return ()
    facts: list[str] = []
    if getattr(risk, "source", None):
        facts.append(f"source={risk.source}")
    level = getattr(risk, "overall_level", None)
    score = getattr(risk, "overall_score", None)
    if level is not None:
        facts.append(f"risk level={level.value}")
    if score is not None:
        facts.append(f"risk score={score:.2f}")
    for signal in getattr(risk, "signals", ())[:3]:
        facts.append(
            f"{signal.label}: category={signal.category.value}, "
            f"level={signal.level.value}, score={signal.score:.2f}"
        )
    return tuple(facts)


def _public_market_facts(context: MeetingContext | None, ticker: str) -> tuple[str, ...]:
    if context is None or context.market is None:
        return ()
    facts: list[str] = []
    for point in context.market.points:
        if point.symbol.upper() != ticker.upper():
            continue
        values = [f"Yahoo/market_data: {point.symbol}"]
        if point.price is not None:
            values.append(f"price={point.price:.2f}")
        if point.daily_change is not None:
            values.append(f"daily_change={point.daily_change:.2f}")
        if point.daily_change_percent is not None:
            values.append(f"daily_change_percent={point.daily_change_percent:.2f}")
        if point.volume is not None:
            values.append(f"volume_bucket={_volume_bucket(point.volume)}")
        if point.pe_ratio is not None:
            values.append(f"pe_ratio={point.pe_ratio:.2f}")
        if point.market_cap is not None:
            values.append(f"market_cap={_large_number_bucket(point.market_cap)}")
        if point.observed_at is not None:
            values.append(f"observed_at={point.observed_at.isoformat()}")
        facts.append(", ".join(values))
    return tuple(facts)


def _profile_facts(context: MeetingContext | None, ticker: str) -> tuple[str, ...]:
    if context is None or context.market is None:
        return ()
    facts: list[str] = []
    for point in context.market.points:
        if point.symbol.upper() != ticker.upper():
            continue
        values = [f"Yahoo/profile: {point.symbol}"]
        sector = _optional_point_text(point, "sector")
        if sector is not None:
            values.append(f"sector={sector}")
        industry = _optional_point_text(point, "industry")
        if industry is not None:
            values.append(f"industry={industry}")
        market_cap = _optional_point_float(point, "market_cap")
        if market_cap is not None:
            values.append(f"market_cap={_large_number_bucket(market_cap)}")
        beta = _optional_point_float(point, "beta")
        if beta is not None:
            values.append(f"beta={beta:.2f}")
        if len(values) > 1:
            facts.append(", ".join(values))
    return tuple(facts)


def _valuation_facts(context: MeetingContext | None, ticker: str) -> tuple[str, ...]:
    if context is None or context.market is None:
        return ()
    facts: list[str] = []
    for point in context.market.points:
        if point.symbol.upper() != ticker.upper():
            continue
        values = [f"Yahoo/valuation: {point.symbol}"]
        trailing_pe = _optional_point_float(point, "pe_ratio")
        if trailing_pe is not None:
            values.append(f"trailing_pe={trailing_pe:.2f}")
        forward_pe = _optional_point_float(point, "forward_pe")
        if forward_pe is not None:
            values.append(f"forward_pe={forward_pe:.2f}")
        enterprise_value = _optional_point_float(point, "enterprise_value")
        if enterprise_value is not None:
            values.append(
                f"enterprise_value={_large_number_bucket(enterprise_value)}"
            )
        revenue_ttm = _optional_point_float(point, "revenue_ttm")
        if revenue_ttm is not None:
            values.append(f"revenue_ttm={_large_number_bucket(revenue_ttm)}")
        ev_to_sales = _optional_point_float(point, "ev_to_sales")
        if ev_to_sales is not None:
            values.append(f"ev_to_sales={ev_to_sales:.2f}")
        if len(values) > 1:
            facts.append(", ".join(values))
    return tuple(facts)


def _company_facts(context: MeetingContext | None, ticker: str) -> tuple[str, ...]:
    if context is None or context.filings is None:
        return ()
    facts: list[str] = []
    for item in context.filings.items:
        if item.symbol.upper() != ticker.upper():
            continue
        values = [f"SEC EDGAR: {item.symbol} {item.filing_type}"]
        if item.filed_at is not None:
            values.append(f"filed_at={item.filed_at.date().isoformat()}")
        if item.accession_number:
            values.append(f"accession_number={item.accession_number}")
        if item.summary:
            values.append(f"summary={item.summary}")
        facts.append(", ".join(values))
    return tuple(facts[:5])


def _news_facts(context: MeetingContext | None, ticker: str) -> tuple[str, ...]:
    if context is None or context.news is None:
        return ()
    facts: list[str] = []
    for item in context.news.items:
        symbol = getattr(item, "symbol", None)
        if symbol is not None and symbol.upper() != ticker.upper():
            continue
        values = [f"Yahoo/news: {ticker}"]
        title = str(getattr(item, "title", "")).strip()
        if not title:
            continue
        values.append(f"title={title}")
        source = str(getattr(item, "source", "")).strip()
        if source:
            values.append(f"publisher={source}")
        published_at = getattr(item, "published_at", None)
        if published_at is not None:
            values.append(f"published_at={published_at.isoformat()}")
        url = str(getattr(item, "url", "") or "").strip()
        if url:
            values.append(f"url={url}")
        facts.append(", ".join(values))
    return tuple(facts[:5])


def _macro_facts(context: MeetingContext | None) -> tuple[str, ...]:
    if context is None:
        return ()
    facts: list[str] = []
    if context.macro is not None:
        facts.extend(f"FRED/macro: {item}" for item in context.macro.indicators)
        if context.macro.summary:
            facts.append(f"FRED/macro summary: {context.macro.summary}")
    if context.economic_regime is not None:
        facts.append(
            "FRED/economic_regime: "
            f"regime={context.economic_regime.regime}, "
            f"confidence={context.economic_regime.confidence}"
        )
        facts.extend(
            f"FRED/economic_regime indicator: {item}"
            for item in context.economic_regime.indicators
        )
    return tuple(facts)


def _volume_bucket(volume: float) -> str:
    if volume < 1_000_000:
        return "low"
    if volume < 10_000_000:
        return "moderate"
    if volume < 50_000_000:
        return "high"
    return "very_high"


def _large_number_bucket(value: float) -> str:
    if value < 2_000_000_000:
        return "small_cap"
    if value < 10_000_000_000:
        return "mid_cap"
    if value < 200_000_000_000:
        return "large_cap"
    return "mega_cap"


def _optional_point_text(point: Any, field_name: str) -> str | None:
    value = getattr(point, field_name, None)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_point_float(point: Any, field_name: str) -> float | None:
    value = getattr(point, field_name, None)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _source_summaries(inputs: _TickerInputs) -> tuple[str, ...]:
    summaries: list[str] = []
    if inputs.holding is not None:
        summaries.append("portfolio: current holding facts")
    if inputs.watchlist_insight is not None:
        summaries.append("watchlist: user thesis and notes")
    if inputs.public_market_facts:
        summaries.append("market_data: public market facts")
    if inputs.profile_facts:
        summaries.append("profile: public Yahoo profile facts")
    if inputs.valuation_facts:
        summaries.append("valuation: public Yahoo valuation facts")
    if inputs.news_facts:
        summaries.append("news: public Yahoo news facts")
    if inputs.company_facts:
        summaries.append("sec_filings: public company filings")
    if inputs.macro_facts:
        summaries.append("macro: public macro facts")
    if inputs.position_context is not None:
        summaries.append("portfolio: privacy-safe bucketed context")
    if inputs.intelligence_context is not None:
        summaries.append("market_context: factual market context")
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
        if _is_connected_factual_context(risk.summary)
    )
    upcoming_catalysts = _unique(
        f"{ticker_report.ticker}: {catalyst.summary}"
        for ticker_report in ticker_reports
        for catalyst in ticker_report.catalysts
        if _is_connected_factual_context(catalyst.summary)
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
            portfolio_summary=_first_existing(
                ticker_report.portfolio_summary
                for ticker_report in ticker_reports
            ),
            position_context=_first_existing(
                ticker_report.position_context
                for ticker_report in ticker_reports
                if len(ticker_reports) == 1
            ),
            public_market_facts=_unique(
                fact
                for ticker_report in ticker_reports
                for fact in ticker_report.public_market_facts
            ),
            profile_facts=_unique(
                fact
                for ticker_report in ticker_reports
                for fact in ticker_report.profile_facts
            ),
            valuation_facts=_unique(
                fact
                for ticker_report in ticker_reports
                for fact in ticker_report.valuation_facts
            ),
            news_facts=_unique(
                fact
                for ticker_report in ticker_reports
                for fact in ticker_report.news_facts
            ),
            company_facts=_unique(
                fact
                for ticker_report in ticker_reports
                for fact in ticker_report.company_facts
            ),
            macro_facts=_unique(
                fact
                for ticker_report in ticker_reports
                for fact in ticker_report.macro_facts
            ),
            advisory_only_disclaimer=ADVISORY_ONLY_DISCLAIMER,
        )
        for member in committee_service.daily_investment_committee()
    )


def _opinion_text(
    opinions: tuple[Any, ...],
    persona_id: str,
) -> str:
    for opinion in opinions:
        if getattr(opinion, "persona_id", "") == persona_id:
            return str(getattr(opinion, "reasoning_summary", "")).strip()
    return "Committee opinion is unavailable for this ticker."


def _ticker_evidence(ticker_report: ResearchTickerReport) -> tuple[str, ...]:
    evidence: list[str] = []
    for finding in ticker_report.findings:
        evidence.append(f"{finding.source}: {finding.summary}")
        evidence.extend(f"{finding.source}: {note}" for note in finding.evidence_notes)
    evidence.extend(ticker_report.public_market_facts)
    evidence.extend(ticker_report.profile_facts)
    evidence.extend(ticker_report.valuation_facts)
    evidence.extend(ticker_report.news_facts)
    evidence.extend(ticker_report.company_facts)
    evidence.extend(ticker_report.macro_facts)
    evidence.extend(_portfolio_summary_evidence(ticker_report.portfolio_summary))
    evidence.extend(_position_context_evidence(ticker_report.position_context))
    for risk in ticker_report.risks:
        if risk.evidence_notes:
            evidence.append(f"risk: {risk.summary}")
            evidence.extend(f"risk evidence: {note}" for note in risk.evidence_notes)
    for catalyst in ticker_report.catalysts:
        if catalyst.evidence_notes:
            evidence.append(f"catalyst: {catalyst.summary}")
            evidence.extend(
                f"catalyst evidence: {note}" for note in catalyst.evidence_notes
            )
    evidence.extend(ticker_report.source_summaries)
    evidence.extend(f"report evidence: {note}" for note in ticker_report.evidence_notes)
    return _unique(tuple(evidence))


def _portfolio_summary_evidence(summary: PortfolioSummary | None) -> tuple[str, ...]:
    if summary is None:
        return ()
    return (
        f"portfolio_summary: privacy_level={summary.privacy_level}",
        f"portfolio_summary: number_of_positions={summary.number_of_positions}",
        f"portfolio_summary: cash_allocation_bucket={summary.cash_allocation_bucket}",
        f"portfolio_summary: concentration_level={summary.concentration_level}",
        f"portfolio_summary: largest_position_bucket={summary.largest_position_bucket}",
        f"portfolio_summary: top5_concentration_bucket={summary.top5_concentration_bucket}",
        f"portfolio_summary: dominant_sector={summary.dominant_sector or 'unknown'}",
        f"portfolio_summary: style_exposure={summary.style_exposure}",
    )


def _position_context_evidence(
    context: PortfolioPositionContext | None,
) -> tuple[str, ...]:
    if context is None:
        return ()
    return (
        f"position_context: ticker={context.ticker}",
        f"position_context: privacy_level={context.privacy_level}",
        f"position_context: is_holding={context.is_holding}",
        f"position_context: position_size_bucket={context.position_size_bucket}",
        f"position_context: portfolio_rank_bucket={context.portfolio_rank_bucket}",
        f"position_context: unrealized_return_bucket={context.unrealized_return_bucket}",
        f"position_context: holding_role={context.holding_role}",
        f"position_context: add_allowed={context.add_allowed}",
        f"position_context: trim_candidate={context.trim_candidate}",
    )


def _is_connected_factual_context(value: str) -> bool:
    return value.strip() != "No connected factual context available."


def _first_existing(values: Any) -> Any | None:
    for value in values:
        if value is not None:
            return value
    return None


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
        notes.append("No market context service connected.")
    return tuple(notes)


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
