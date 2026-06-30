"""Prompt rendering helpers for Context Layer models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from parakeetnest.context.models import (
    FilingSnapshot,
    FinancialStatementSnapshot,
    KnowledgeBaseSnapshot,
    MacroSnapshot,
    MarketSnapshot,
    MeetingContext,
    NewsContext,
    PortfolioSnapshot,
    ValuationContextSnapshot,
)


@dataclass(frozen=True)
class MeetingContextPromptRenderer:
    """Render a MeetingContext into prompt-ready markdown sections."""

    def render(self, context: MeetingContext) -> str:
        """Return a stable, compact markdown representation of meeting context."""
        return "\n\n".join(
            (
                "## Metadata\n" + self._render_metadata(context),
                "## Market\n" + self._render_market(context.market),
                "## News\n" + self._render_news(context.news),
                "## Filings\n" + self._render_filings(context.filings),
                "## Financial Statements\n"
                + self._render_financials(context.financials),
                "## Valuation\n" + self._render_valuation(context.valuation),
                "## Portfolio\n" + self._render_portfolio(context.portfolio),
                "## Macro\n" + self._render_macro(context.macro),
                "## Knowledge Base\n"
                + self._render_knowledge_base(context.knowledge_base),
            )
        )

    @classmethod
    def _render_metadata(cls, context: MeetingContext) -> str:
        metadata = context.metadata
        return "\n".join(
            (
                f"- Generated at: {cls._format_value(metadata.generated_at)}",
                f"- Sources: {cls._format_sequence(metadata.sources)}",
                f"- Warnings: {cls._format_sequence(metadata.warnings)}",
                "- Data quality notes: "
                + cls._format_sequence(metadata.data_quality_notes),
            )
        )

    @classmethod
    def _render_snapshot_header(
        cls,
        source: str,
        fetched_at: datetime | None,
    ) -> str:
        return "- Snapshot: " + cls._format_fields(
            (("source", source), ("fetched_at", fetched_at))
        )

    @classmethod
    def _format_fields(cls, fields: tuple[tuple[str, Any], ...]) -> str:
        formatted = [
            f"{name}={cls._format_value(value)}"
            for name, value in fields
            if value is not None
        ]
        return ", ".join(formatted) if formatted else "None"

    @staticmethod
    def _format_value(value: Any) -> str:
        if value is None:
            return "None"
        if isinstance(value, datetime | date):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _format_sequence(values: tuple[str, ...]) -> str:
        return ", ".join(values) if values else "None"

    @staticmethod
    def _render_market(market: MarketSnapshot | None) -> str:
        if market is None or not market.points:
            return "- No market data available."
        lines = [
            MeetingContextPromptRenderer._render_snapshot_header(
                market.source, market.fetched_at
            )
        ]
        lines.extend(
            "- "
            + point.symbol
            + ": "
            + MeetingContextPromptRenderer._format_fields(
                (
                    ("price", point.price),
                    ("daily_change", point.daily_change),
                    ("daily_change_percent", point.daily_change_percent),
                    ("volume", point.volume),
                    ("market_cap", point.market_cap),
                    ("pe_ratio", point.pe_ratio),
                    ("eps", point.eps),
                    ("observed_at", point.observed_at),
                    ("source", point.source),
                )
            )
            for point in market.points
        )
        return "\n".join(lines)

    @staticmethod
    def _render_news(news: NewsContext | None) -> str:
        if news is None or not news.items:
            return "- No news available."
        lines = [
            MeetingContextPromptRenderer._render_snapshot_header(
                news.source, news.fetched_at
            )
        ]
        lines.extend(
            "- "
            + (item.symbol or "Market")
            + ": "
            + item.title
            + MeetingContextPromptRenderer._format_optional_sentence(item.summary)
            + MeetingContextPromptRenderer._format_parenthetical_fields(
                (
                    ("source", item.source),
                    ("published_at", item.published_at),
                    ("url", item.url),
                )
            )
            for item in news.items
        )
        return "\n".join(lines)

    @staticmethod
    def _render_filings(filings: FilingSnapshot | None) -> str:
        if filings is None or not filings.items:
            return "- No filings available."
        lines = [
            MeetingContextPromptRenderer._render_snapshot_header(
                filings.source, filings.fetched_at
            )
        ]
        lines.extend(
            "- "
            + item.symbol
            + ": "
            + item.filing_type
            + MeetingContextPromptRenderer._format_optional_sentence(item.summary)
            + MeetingContextPromptRenderer._format_parenthetical_fields(
                (
                    ("source", item.source),
                    ("filed_at", item.filed_at),
                    ("accession_number", item.accession_number),
                    ("url", item.url),
                )
            )
            for item in filings.items
        )
        return "\n".join(lines)

    @staticmethod
    def _render_financials(
        financials: FinancialStatementSnapshot | None,
    ) -> str:
        if financials is None or not financials.items:
            return "- No financial statements available."
        lines = [
            MeetingContextPromptRenderer._render_snapshot_header(
                financials.source, financials.fetched_at
            )
        ]
        lines.extend(
            "- "
            + item.symbol
            + " "
            + item.period_type
            + ": "
            + MeetingContextPromptRenderer._format_fields(
                (
                    ("revenue", item.revenue),
                    ("gross_profit", item.gross_profit),
                    ("operating_income", item.operating_income),
                    ("net_income", item.net_income),
                    ("eps", item.eps),
                    ("cash", item.cash),
                    ("total_debt", item.total_debt),
                    ("total_equity", item.total_equity),
                    ("operating_cash_flow", item.operating_cash_flow),
                    ("free_cash_flow", item.free_cash_flow),
                    ("fiscal_year", item.fiscal_year),
                    ("fiscal_quarter", item.fiscal_quarter),
                    ("currency", item.currency),
                    ("source", item.source),
                )
            )
            for item in financials.items
        )
        return "\n".join(lines)

    @staticmethod
    def _render_valuation(
        valuation: ValuationContextSnapshot | None,
    ) -> str:
        if valuation is None or not valuation.items:
            return "- No valuation context available."
        lines = [
            MeetingContextPromptRenderer._render_snapshot_header(
                valuation.source, valuation.fetched_at
            )
        ]
        for item in valuation.items:
            fields = (
                ("as_of_date", item.as_of_date),
                ("fiscal_period", item.fiscal_period),
                ("metrics", MeetingContextPromptRenderer._format_mapping(item.metrics)),
                (
                    "calculation_notes",
                    MeetingContextPromptRenderer._format_sequence(
                        item.calculation_notes
                    ),
                ),
                ("confidence", item.confidence),
                (
                    "data_sources",
                    MeetingContextPromptRenderer._format_sequence(item.data_sources),
                ),
            )
            lines.append(
                "- "
                + item.symbol
                + ": "
                + MeetingContextPromptRenderer._format_fields(fields)
            )
        return "\n".join(lines)

    @staticmethod
    def _render_portfolio(portfolio: PortfolioSnapshot | None) -> str:
        if portfolio is None:
            return "- No portfolio data available."
        lines = [
            MeetingContextPromptRenderer._render_snapshot_header(
                portfolio.source, portfolio.fetched_at
            ),
            f"- Total value: {portfolio.total_value}",
            f"- Cash balance: {portfolio.cash_balance}",
        ]
        if not portfolio.positions:
            lines.append("- Positions: None")
            return "\n".join(lines)
        lines.append("- Positions:")
        lines.extend(
            "  - "
            + position.symbol
            + ": "
            + MeetingContextPromptRenderer._format_fields(
                (
                    ("quantity", position.quantity),
                    ("market_value", position.market_value),
                    ("cost_basis", position.cost_basis),
                    ("unrealized_pl", position.unrealized_pl),
                    ("weight", position.weight),
                )
            )
            for position in portfolio.positions
        )
        return "\n".join(lines)

    @staticmethod
    def _render_macro(macro: MacroSnapshot | None) -> str:
        if macro is None:
            return "- No macro context available."
        lines = [
            MeetingContextPromptRenderer._render_snapshot_header(
                macro.source, macro.fetched_at
            )
        ]
        if macro.summary:
            lines.append(f"- Summary: {macro.summary}")
        if macro.observed_on:
            lines.append(f"- Observed on: {macro.observed_on.isoformat()}")
        lines.extend(f"- {indicator}" for indicator in macro.indicators)
        return "\n".join(lines) if len(lines) > 1 else "- No macro context available."

    @staticmethod
    def _render_knowledge_base(
        knowledge_base: KnowledgeBaseSnapshot | None,
    ) -> str:
        if knowledge_base is None:
            return "- No knowledge base context available."
        lines = [
            MeetingContextPromptRenderer._render_snapshot_header(
                knowledge_base.source, knowledge_base.fetched_at
            )
        ]
        lines.extend(f"- Thesis: {item}" for item in knowledge_base.thesis)
        lines.extend(f"- Discussion: {item}" for item in knowledge_base.discussions)
        lines.extend(f"- Note: {item}" for item in knowledge_base.research_notes)
        lines.extend(f"- Lesson: {item}" for item in knowledge_base.lessons_learned)
        return (
            "\n".join(lines)
            if len(lines) > 1
            else "- No knowledge base context available."
        )

    @staticmethod
    def _format_optional_sentence(value: str | None) -> str:
        return f". {value}" if value else ""

    @staticmethod
    def _format_mapping(values: dict[str, float | None]) -> str:
        if not values:
            return "None"
        return "; ".join(f"{key}={value}" for key, value in sorted(values.items()))

    @staticmethod
    def _format_parenthetical_fields(fields: tuple[tuple[str, Any], ...]) -> str:
        formatted = MeetingContextPromptRenderer._format_fields(fields)
        return f" ({formatted})" if formatted != "None" else ""
