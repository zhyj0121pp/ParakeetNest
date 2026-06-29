"""Tests for Market Data Layer domain exceptions."""

from parakeetnest.market_data import (
    InvalidSymbolError,
    MalformedMarketDataError,
    MarketDataError,
    ProviderUnavailableError,
    RateLimitError,
    Symbol,
)


def test_market_data_error_hierarchy_is_provider_independent() -> None:
    """Domain failures should share a single provider-neutral base class."""
    symbol = Symbol("aapl")
    errors = [
        InvalidSymbolError("invalid", symbol=symbol),
        ProviderUnavailableError("unavailable", symbol=symbol, details="timeout"),
        RateLimitError("rate limited", symbol=symbol),
        MalformedMarketDataError("malformed", symbol=symbol),
    ]

    assert all(isinstance(error, MarketDataError) for error in errors)
    assert errors[0].code == "invalid_symbol"
    assert errors[1].retryable is True
    assert errors[1].details == "timeout"
    assert errors[2].code == "rate_limited"
    assert errors[3].symbol == Symbol("AAPL")
