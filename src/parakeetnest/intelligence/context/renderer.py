"""Markdown rendering for Investment Intelligence Context snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import Any

from parakeetnest.intelligence.context.models import InvestmentIntelligenceContext


class InvestmentIntelligenceRenderer:
    """Render unified investment intelligence into deterministic Markdown."""

    def render(self, context: InvestmentIntelligenceContext) -> str:
        """Render the context into committee-consumable Markdown."""
        sections = [
            "# Investment Intelligence Context",
            "",
            f"Generated At: {context.generated_at.isoformat()}",
            "",
            self._render_economic_regime(context),
            self._render_sector_rotation(context),
            self._render_risk(context),
            self._render_breadth(context),
            self._render_momentum(context),
            self._render_sentiment(context),
            self._render_health(context),
        ]
        return "\n".join(section.rstrip() for section in sections).rstrip() + "\n"

    def _render_economic_regime(self, context: InvestmentIntelligenceContext) -> str:
        snapshot = context.economic_regime
        lines = [
            "## Economic Regime",
            f"- Regime: {self._value(snapshot.regime)}",
            f"- Confidence: {self._value(snapshot.confidence)}",
            f"- As Of: {snapshot.as_of_date.isoformat()}",
        ]
        if snapshot.summary:
            lines.append(f"- Summary: {snapshot.summary}")
        if snapshot.indicators:
            lines.append("- Indicators:")
            for indicator in snapshot.indicators:
                detail = self._join_present(
                    [
                        indicator.name,
                        self._number("value", indicator.value),
                        self._optional("unit", indicator.unit),
                        self._optional("interpretation", indicator.interpretation),
                    ]
                )
                lines.append(f"  - {detail}")
        return "\n".join(lines)

    def _render_sector_rotation(self, context: InvestmentIntelligenceContext) -> str:
        snapshot = context.sector_rotation
        lines = [
            "## Sector Rotation",
            f"- As Of: {snapshot.as_of_date.isoformat()}",
        ]
        if snapshot.summary:
            lines.append(f"- Summary: {snapshot.summary}")
        if snapshot.signals:
            lines.append("- Signals:")
            for signal in snapshot.signals:
                lines.append(
                    "  - "
                    + self._join_present(
                        [
                            signal.sector.name,
                            self._optional("classification", signal.classification),
                            self._optional("confidence", signal.confidence),
                        ]
                    )
                )
        return "\n".join(lines)

    def _render_risk(self, context: InvestmentIntelligenceContext) -> str:
        assessment = context.risk
        lines = [
            "## Risk",
            f"- Overall Level: {self._value(assessment.overall_level)}",
            f"- Overall Score: {assessment.overall_score:.2f}",
        ]
        if assessment.as_of_date is not None:
            lines.append(f"- As Of: {assessment.as_of_date.isoformat()}")
        if assessment.summary:
            lines.append(f"- Summary: {assessment.summary}")
        if assessment.signals:
            lines.append("- Signals:")
            for signal in assessment.signals:
                lines.append(
                    "  - "
                    + self._join_present(
                        [
                            signal.label,
                            self._optional("category", signal.category),
                            self._optional("level", signal.level),
                            self._number("score", signal.score),
                        ]
                    )
                )
        return "\n".join(lines)

    def _render_breadth(self, context: InvestmentIntelligenceContext) -> str:
        snapshot = context.breadth
        lines = [
            "## Market Breadth",
            f"- Universe: {snapshot.universe}",
            f"- Date: {snapshot.date.isoformat()}",
            f"- Regime: {self._value(snapshot.breadth_regime)}",
            f"- Score: {snapshot.breadth_score:.2f}",
            f"- Advancers / Decliners / Unchanged: "
            f"{snapshot.advancers} / {snapshot.decliners} / {snapshot.unchanged}",
            f"- Percent Above 200D MA: {snapshot.percent_above_200d_ma:.2f}",
        ]
        lines.extend(self._render_tuple("Warnings", snapshot.warnings))
        return "\n".join(lines)

    def _render_momentum(self, context: InvestmentIntelligenceContext) -> str:
        snapshot = context.momentum
        lines = [
            "## Momentum",
            f"- Symbol: {snapshot.symbol}",
            f"- As Of: {snapshot.as_of.isoformat()}",
            f"- Regime: {self._value(snapshot.momentum_regime)}",
            f"- Score: {snapshot.momentum_score:.2f}",
            f"- Reversal Risk: {self._value(snapshot.reversal_risk)}",
            f"- Confidence: {snapshot.confidence:.2f}",
        ]
        lines.extend(self._render_tuple("Evidence", snapshot.evidence))
        return "\n".join(lines)

    def _render_sentiment(self, context: InvestmentIntelligenceContext) -> str:
        snapshot = context.sentiment
        lines = [
            "## Market Sentiment",
            f"- As Of: {snapshot.as_of.isoformat()}",
            f"- Regime: {self._value(snapshot.regime)}",
            f"- Overall Score: {snapshot.overall_score:.2f}",
            f"- Confidence: {snapshot.confidence:.2f}",
        ]
        if snapshot.summary:
            lines.append(f"- Summary: {snapshot.summary}")
        if snapshot.signals:
            lines.append("- Signals:")
            for signal in sorted(snapshot.signals, key=lambda item: item.name.lower()):
                lines.append(
                    "  - "
                    + self._join_present(
                        [
                            signal.name,
                            self._number("value", signal.value),
                            self._number("score", signal.normalized_score),
                            self._number("weight", signal.weight),
                        ]
                    )
                )
        return "\n".join(lines)

    def _render_health(self, context: InvestmentIntelligenceContext) -> str:
        snapshot = context.health
        lines = [
            "## Market Health",
            f"- Universe: {snapshot.universe}",
            f"- As Of: {snapshot.as_of.isoformat()}",
            f"- State: {self._value(snapshot.health_state)}",
            f"- Score: {snapshot.health_score:.2f}",
            f"- Confidence: {snapshot.confidence:.2f}",
        ]
        lines.extend(self._render_tuple("Positives", snapshot.positives))
        lines.extend(self._render_tuple("Negatives", snapshot.negatives))
        lines.extend(self._render_tuple("Warnings", snapshot.warnings))
        if snapshot.components:
            lines.append("- Components:")
            for component in sorted(snapshot.components, key=lambda item: item.name):
                lines.append(
                    "  - "
                    + self._join_present(
                        [
                            component.name,
                            self._optional("state", component.state),
                            self._number("score", component.score),
                            self._number("weight", component.weight),
                        ]
                    )
                )
        return "\n".join(lines)

    def _render_tuple(self, label: str, values: Iterable[str]) -> list[str]:
        normalized = tuple(value.strip() for value in values if value.strip())
        if not normalized:
            return []
        return [f"- {label}:"] + [f"  - {value}" for value in normalized]

    def _value(self, value: Any) -> str:
        if value is None:
            return "N/A"
        if isinstance(value, Enum):
            return value.value
        return str(value)

    def _optional(self, label: str, value: Any) -> str | None:
        if value is None:
            return None
        return f"{label}={self._value(value)}"

    def _number(self, label: str, value: float | None) -> str | None:
        if value is None:
            return None
        return f"{label}={float(value):.2f}"

    def _join_present(self, values: Iterable[str | None]) -> str:
        return "; ".join(value for value in values if value)


__all__ = ["InvestmentIntelligenceRenderer"]
