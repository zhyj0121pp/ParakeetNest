"""Provider-neutral position context builder service."""

from __future__ import annotations

from collections.abc import Iterable

from parakeetnest.context.models import (
    KnowledgeBaseSnapshot,
    MarketSnapshot,
    NewsContext,
    ValuationContextSnapshot,
)
from parakeetnest.models import PositionContext


class PositionContextBuilder:
    """Build committee-ready context for one current portfolio position."""

    def build(
        self,
        position: object,
        *,
        market: MarketSnapshot | None = None,
        news: NewsContext | None = None,
        valuation: ValuationContextSnapshot | None = None,
        knowledge_base: KnowledgeBaseSnapshot | None = None,
        relevant_research: Iterable[str] = (),
        risk_notes: Iterable[str] = (),
        valuation_notes: Iterable[str] = (),
        momentum_notes: Iterable[str] = (),
        portfolio_notes: Iterable[str] = (),
    ) -> PositionContext:
        """Return one normalized PositionContext from already-available inputs."""
        symbol = _symbol_for(position)
        market_point = _matching_item(symbol, _items(market, "points"))
        valuation_item = _matching_item(symbol, _items(valuation, "items"))

        quantity = _required_number(_value(position, "quantity"), "quantity")
        market_value = _position_market_value(position)
        current_price = _number(_value(position, "current_price"))
        if current_price is None:
            current_price = _number(_value(market_point, "price"))

        return PositionContext(
            symbol=symbol,
            company_name=_company_name_for(position, symbol),
            quantity=quantity,
            market_value=market_value,
            portfolio_weight=_portfolio_weight_for(position),
            cost_basis=_cost_basis_for(position, quantity),
            unrealized_gain_loss=_first_number(
                _value(position, "unrealized_gain_loss"),
                _value(position, "unrealized_pl"),
            ),
            current_price=current_price,
            recent_price_change=_recent_price_change_for(market_point),
            relevant_news=_news_for(symbol, news),
            relevant_research=(
                *_research_for(symbol, knowledge_base),
                *_text_tuple(relevant_research),
            ),
            risk_notes=_text_tuple(risk_notes),
            valuation_notes=(
                *_valuation_notes_for(valuation_item),
                *_text_tuple(valuation_notes),
            ),
            momentum_notes=_text_tuple(momentum_notes),
            portfolio_notes=_text_tuple(portfolio_notes),
        )

    def __call__(
        self,
        position: object,
        *,
        market: MarketSnapshot | None = None,
        news: NewsContext | None = None,
        valuation: ValuationContextSnapshot | None = None,
        knowledge_base: KnowledgeBaseSnapshot | None = None,
        relevant_research: Iterable[str] = (),
        risk_notes: Iterable[str] = (),
        valuation_notes: Iterable[str] = (),
        momentum_notes: Iterable[str] = (),
        portfolio_notes: Iterable[str] = (),
    ) -> PositionContext:
        """Allow the builder to be injected anywhere a callable is expected."""
        return self.build(
            position,
            market=market,
            news=news,
            valuation=valuation,
            knowledge_base=knowledge_base,
            relevant_research=relevant_research,
            risk_notes=risk_notes,
            valuation_notes=valuation_notes,
            momentum_notes=momentum_notes,
            portfolio_notes=portfolio_notes,
        )


def _symbol_for(position: object) -> str:
    symbol = _value(position, "symbol")
    if symbol is None:
        symbol = _value(position, "ticker")
    if not isinstance(symbol, str):
        raise ValueError("position symbol is required")
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("position symbol is required")
    return normalized


def _company_name_for(position: object, symbol: str) -> str:
    for field_name in ("company_name", "name"):
        value = _value(position, field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return symbol


def _position_market_value(position: object) -> float:
    market_value = _number(_value(position, "market_value"))
    if market_value is not None:
        return market_value
    quantity = _required_number(_value(position, "quantity"), "quantity")
    current_price = _required_number(_value(position, "current_price"), "current_price")
    return quantity * current_price


def _portfolio_weight_for(position: object) -> float:
    return _first_number(
        _value(position, "portfolio_weight"),
        _value(position, "weight"),
        default=0.0,
    )


def _cost_basis_for(position: object, quantity: float) -> float | None:
    cost_basis = _number(_value(position, "cost_basis"))
    if cost_basis is not None:
        return cost_basis
    average_cost = _number(_value(position, "average_cost"))
    if average_cost is not None:
        return quantity * average_cost
    return None


def _recent_price_change_for(market_point: object | None) -> float | None:
    return _first_number(
        _value(market_point, "daily_change_percent"),
        _value(market_point, "daily_change"),
    )


def _news_for(symbol: str, news: NewsContext | None) -> tuple[str, ...]:
    summaries: list[str] = []
    for item in _items(news, "items"):
        item_symbol = _value(item, "symbol")
        if isinstance(item_symbol, str) and item_symbol.strip().upper() != symbol:
            continue
        title = _value(item, "title")
        summary = _value(item, "summary")
        text = " - ".join(
            part.strip()
            for part in (title, summary)
            if isinstance(part, str) and part.strip()
        )
        if text:
            summaries.append(text)
    return tuple(summaries)


def _research_for(
    symbol: str,
    knowledge_base: KnowledgeBaseSnapshot | None,
) -> tuple[str, ...]:
    notes: list[str] = []
    for field_name in ("thesis", "discussions", "research_notes", "lessons_learned"):
        for note in _items(knowledge_base, field_name):
            if isinstance(note, str) and symbol in note.upper():
                notes.append(note)
    return _text_tuple(notes)


def _valuation_notes_for(valuation_item: object | None) -> tuple[str, ...]:
    return _text_tuple(_items(valuation_item, "calculation_notes"))


def _matching_item(symbol: str, items: Iterable[object]) -> object | None:
    for item in items:
        item_symbol = _value(item, "symbol")
        if isinstance(item_symbol, str) and item_symbol.strip().upper() == symbol:
            return item
    return None


def _items(container: object | None, field_name: str) -> tuple[object, ...]:
    value = _value(container, field_name)
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def _value(item: object | None, field_name: str) -> object | None:
    if item is None:
        return None
    if isinstance(item, dict):
        return item.get(field_name)
    return getattr(item, field_name, None)


def _required_number(value: object, field_name: str) -> float:
    number = _number(value)
    if number is None:
        raise ValueError(f"position {field_name} is required")
    return number


def _first_number(*values: object, default: float | None = None) -> float | None:
    for value in values:
        number = _number(value)
        if number is not None:
            return number
    return default


def _number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _text_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(value.strip() for value in values if value.strip())


__all__ = ["PositionContextBuilder"]
