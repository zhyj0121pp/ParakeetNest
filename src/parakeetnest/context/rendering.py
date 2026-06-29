"""Prompt rendering helpers for Context Layer models."""

from __future__ import annotations

from dataclasses import dataclass

from parakeetnest.context.models import (
    KnowledgeBaseSnapshot,
    MacroSnapshot,
    MarketSnapshot,
    MeetingContext,
    NewsSnapshot,
    PortfolioSnapshot,
)


@dataclass(frozen=True)
class MeetingContextPromptRenderer:
    """Render a MeetingContext into prompt-ready markdown sections."""

    def render(self, context: MeetingContext) -> str:
        """Return a stable, compact markdown representation of meeting context."""
        return "\n\n".join(
            (
                "## Market\n" + self._render_market(context.market),
                "## News\n" + self._render_news(context.news),
                "## Portfolio\n" + self._render_portfolio(context.portfolio),
                "## Macro\n" + self._render_macro(context.macro),
                "## Knowledge Base\n"
                + self._render_knowledge_base(context.knowledge_base),
            )
        )

    @staticmethod
    def _render_market(market: MarketSnapshot | None) -> str:
        if market is None or not market.points:
            return "- None"
        return "\n".join(
            (
                f"- {point.symbol}: price={point.price}, "
                f"change={point.daily_change_percent}%, "
                f"volume={point.volume}, source={point.source}"
            )
            for point in market.points
        )

    @staticmethod
    def _render_news(news: NewsSnapshot | None) -> str:
        if news is None or not news.items:
            return "- None"
        return "\n".join(
            f"- {item.symbol or 'Market'}: {item.title}. {item.summary or ''}".strip()
            for item in news.items
        )

    @staticmethod
    def _render_portfolio(portfolio: PortfolioSnapshot | None) -> str:
        if portfolio is None:
            return "- None"
        lines = [
            f"- Total value: {portfolio.total_value}",
            f"- Cash balance: {portfolio.cash_balance}",
        ]
        if not portfolio.positions:
            lines.append("- Positions: None")
            return "\n".join(lines)
        lines.extend(
            (
                f"- {position.symbol}: quantity={position.quantity}, "
                f"market_value={position.market_value}, weight={position.weight}"
            )
            for position in portfolio.positions
        )
        return "\n".join(lines)

    @staticmethod
    def _render_macro(macro: MacroSnapshot | None) -> str:
        if macro is None:
            return "- None"
        lines = []
        if macro.summary:
            lines.append(f"- Summary: {macro.summary}")
        lines.extend(f"- {indicator}" for indicator in macro.indicators)
        return "\n".join(lines) if lines else "- None"

    @staticmethod
    def _render_knowledge_base(
        knowledge_base: KnowledgeBaseSnapshot | None,
    ) -> str:
        if knowledge_base is None:
            return "- None"
        lines = []
        lines.extend(f"- Thesis: {item}" for item in knowledge_base.thesis)
        lines.extend(f"- Discussion: {item}" for item in knowledge_base.discussions)
        lines.extend(f"- Note: {item}" for item in knowledge_base.research_notes)
        lines.extend(f"- Lesson: {item}" for item in knowledge_base.lessons_learned)
        return "\n".join(lines) if lines else "- None"
