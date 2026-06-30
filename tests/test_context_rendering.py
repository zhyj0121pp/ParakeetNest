"""Tests for prompt-ready Context Layer rendering."""

from __future__ import annotations

from datetime import UTC, date, datetime

from parakeetnest.context import (
    ContextMetadata,
    ContextRequest,
    EconomicRegimeContextSnapshot,
    FilingItem,
    FilingSnapshot,
    KnowledgeBaseSnapshot,
    MacroSnapshot,
    MarketDataPoint,
    MarketSnapshot,
    MeetingContext,
    MeetingContextPromptRenderer,
    NewsContext,
    NewsItem,
    PortfolioPosition,
    PortfolioSnapshot,
    SectorRotationContextSnapshot,
    ValuationContextItem,
    ValuationContextSnapshot,
)


def test_renderer_outputs_structured_empty_context() -> None:
    context = MeetingContext(
        request=ContextRequest(
            question="Should we add to NVDA?",
            symbols=("NVDA",),
        )
    )

    rendered = MeetingContextPromptRenderer().render(context)

    assert rendered == "\n\n".join(
        (
            "## Metadata\n"
            "- Generated at: None\n"
            "- Sources: None\n"
            "- Warnings: None\n"
            "- Data quality notes: None",
            "## Market\n- No market data available.",
            "## News\n- No news available.",
            "## Filings\n- No filings available.",
            "## Financial Statements\n- No financial statements available.",
            "## Valuation\n- No valuation context available.",
            "## Portfolio\n- No portfolio data available.",
            "## Macro\n- No macro context available.",
            "## Economic Regime\n- No economic regime context available.",
            "## Sector Rotation\n- No sector rotation context available.",
            "## Knowledge Base\n- No knowledge base context available.",
        )
    )


def test_renderer_outputs_stable_markdown_for_populated_context() -> None:
    generated_at = datetime(2026, 6, 29, 13, 0, tzinfo=UTC)
    published_at = datetime(2026, 6, 29, 12, 30, tzinfo=UTC)
    context = MeetingContext(
        request=ContextRequest(
            question="Review AMD.",
            symbols=("AMD",),
            as_of=generated_at,
        ),
        metadata=ContextMetadata(
            generated_at=generated_at,
            sources=(
                "market_provider",
                "news_provider",
                "filings_provider",
                "knowledge_base",
            ),
            warnings=("news feed delayed",),
            data_quality_notes=("quotes are delayed 15 minutes",),
        ),
        market=MarketSnapshot(
            source="market_provider",
            fetched_at=generated_at,
            points=(
                MarketDataPoint(
                    symbol="AMD",
                    source="mock_market",
                    observed_at=generated_at,
                    price=175.25,
                    daily_change_percent=1.2,
                    volume=1000000,
                ),
            ),
        ),
        news=NewsContext(
            source="news_provider",
            fetched_at=generated_at,
            items=(
                NewsItem(
                    title="AMD expands AI accelerator roadmap",
                    source="mock_news",
                    symbol="AMD",
                    url="https://example.test/amd",
                    summary="Management highlighted data center demand.",
                    published_at=published_at,
                ),
            ),
        ),
        filings=FilingSnapshot(
            source="filings_provider",
            fetched_at=generated_at,
            items=(
                FilingItem(
                    symbol="AMD",
                    filing_type="10-Q",
                    source="sec",
                    filed_at=date(2026, 6, 28),
                    accession_number="0000000000-26-000001",
                    summary="Quarterly filing notes inventory risk.",
                ),
            ),
        ),
        valuation=ValuationContextSnapshot(
            source="valuation",
            fetched_at=generated_at,
            items=(
                ValuationContextItem(
                    symbol="AMD",
                    as_of_date=date(2026, 6, 29),
                    fiscal_period="TTM",
                    metrics={"pe_ratio": 35.0, "ps_ratio": 8.5},
                    calculation_notes=("Calculated from normalized inputs.",),
                    confidence="medium",
                    data_sources=("market snapshot", "financial statements"),
                ),
            ),
        ),
        portfolio=PortfolioSnapshot(
            source="portfolio_provider",
            fetched_at=generated_at,
            positions=(
                PortfolioPosition(
                    symbol="AMD",
                    quantity=10,
                    market_value=1752.5,
                    cost_basis=1400.0,
                    unrealized_pl=352.5,
                    weight=0.08,
                ),
            ),
            cash_balance=500.0,
            total_value=2252.5,
        ),
        macro=MacroSnapshot(
            source="macro_provider",
            fetched_at=generated_at,
            indicators=("Rates remain restrictive.",),
            observed_on=date(2026, 6, 29),
            summary="Liquidity is mixed.",
        ),
        economic_regime=EconomicRegimeContextSnapshot(
            source="economic_regime",
            fetched_at=generated_at,
            regime="expansion",
            confidence="high",
            observed_on=date(2026, 6, 29),
            indicators=("GDP Growth (growth): 2.4 percent as of 2026-06-29",),
            summary="Growth is resilient.",
            regime_source="economic_regime_service",
        ),
        sector_rotation=SectorRotationContextSnapshot(
            source="sector_rotation_calculator",
            fetched_at=generated_at,
            as_of_date=date(2026, 6, 29),
            summary="Technology leads while defensives weaken.",
            leaders=("Technology",),
            improving=("Industrials",),
            weakening=("Utilities",),
            laggards=("Real Estate",),
            unknown=("Materials",),
            evidence=(
                "Technology: Relative return classified as leading.",
                "Utilities: Relative return classified as weakening.",
            ),
        ),
        knowledge_base=KnowledgeBaseSnapshot(
            source="knowledge_base",
            fetched_at=generated_at,
            thesis=("Own if AI share gains continue.",),
            discussions=("Prior committee wanted margin evidence.",),
            research_notes=("Watch MI300 customer concentration.",),
            lessons_learned=("Do not chase semis without valuation support.",),
        ),
    )

    rendered = MeetingContextPromptRenderer().render(context)

    assert rendered == "\n\n".join(
        (
            "## Metadata\n"
            "- Generated at: 2026-06-29T13:00:00+00:00\n"
            "- Sources: market_provider, news_provider, filings_provider, "
            "knowledge_base\n"
            "- Warnings: news feed delayed\n"
            "- Data quality notes: quotes are delayed 15 minutes",
            "## Market\n"
            "- Snapshot: source=market_provider, fetched_at=2026-06-29T13:00:00+00:00\n"
            "- AMD: price=175.25, daily_change_percent=1.2, volume=1000000, "
            "observed_at=2026-06-29T13:00:00+00:00, source=mock_market",
            "## News\n"
            "- Snapshot: source=news_provider, fetched_at=2026-06-29T13:00:00+00:00\n"
            "- AMD: AMD expands AI accelerator roadmap. "
            "Management highlighted data center demand. "
            "(source=mock_news, published_at=2026-06-29T12:30:00+00:00, "
            "url=https://example.test/amd)",
            "## Filings\n"
            "- Snapshot: source=filings_provider, fetched_at=2026-06-29T13:00:00+00:00\n"
            "- AMD: 10-Q. Quarterly filing notes inventory risk. "
            "(source=sec, filed_at=2026-06-28, "
            "accession_number=0000000000-26-000001)",
            "## Financial Statements\n- No financial statements available.",
            "## Valuation\n"
            "- Snapshot: source=valuation, fetched_at=2026-06-29T13:00:00+00:00\n"
            "- AMD: as_of_date=2026-06-29, fiscal_period=TTM, "
            "metrics=pe_ratio=35.0; ps_ratio=8.5, "
            "calculation_notes=Calculated from normalized inputs., "
            "confidence=medium, data_sources=market snapshot, financial statements",
            "## Portfolio\n"
            "- Snapshot: source=portfolio_provider, fetched_at=2026-06-29T13:00:00+00:00\n"
            "- Total value: 2252.5\n"
            "- Cash balance: 500.0\n"
            "- Positions:\n"
            "  - AMD: quantity=10, market_value=1752.5, cost_basis=1400.0, "
            "unrealized_pl=352.5, weight=0.08",
            "## Macro\n"
            "- Snapshot: source=macro_provider, fetched_at=2026-06-29T13:00:00+00:00\n"
            "- Summary: Liquidity is mixed.\n"
            "- Observed on: 2026-06-29\n"
            "- Rates remain restrictive.",
            "## Economic Regime\n"
            "- Snapshot: source=economic_regime, fetched_at=2026-06-29T13:00:00+00:00\n"
            "- Current regime: expansion\n"
            "- Confidence: high\n"
            "- Observed on: 2026-06-29\n"
            "- Summary: Growth is resilient.\n"
            "- Source: economic_regime_service\n"
            "- Supporting indicators:\n"
            "  - GDP Growth (growth): 2.4 percent as of 2026-06-29",
            "## Sector Rotation\n"
            "- Snapshot: source=sector_rotation_calculator, "
            "fetched_at=2026-06-29T13:00:00+00:00\n"
            "- As of: 2026-06-29\n"
            "- Summary: Technology leads while defensives weaken.\n"
            "- Leading sectors: Technology\n"
            "- Improving sectors: Industrials\n"
            "- Weakening sectors: Utilities\n"
            "- Lagging sectors: Real Estate\n"
            "- Unknown sectors: Materials\n"
            "- Evidence:\n"
            "  - Technology: Relative return classified as leading.\n"
            "  - Utilities: Relative return classified as weakening.\n"
            "- Source: sector_rotation_calculator",
            "## Knowledge Base\n"
            "- Snapshot: source=knowledge_base, fetched_at=2026-06-29T13:00:00+00:00\n"
            "- Thesis: Own if AI share gains continue.\n"
            "- Discussion: Prior committee wanted margin evidence.\n"
            "- Note: Watch MI300 customer concentration.\n"
            "- Lesson: Do not chase semis without valuation support.",
        )
    )
