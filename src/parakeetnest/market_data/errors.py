"""Provider-independent market data exceptions."""

from __future__ import annotations

from parakeetnest.market_data.models import Symbol


class MarketDataError(Exception):
    """Base class for provider-independent market data failures."""

    code = "market_data_error"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        symbol: Symbol | None = None,
        details: str | None = None,
        cause: BaseException | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.symbol = symbol
        self.details = details
        self.cause = cause
        if retryable is not None:
            self.retryable = retryable


class ProviderUnavailableError(MarketDataError):
    """Raised when a provider is temporarily unable to fulfill a request."""

    code = "provider_unavailable"
    retryable = True


class InvalidSymbolError(MarketDataError):
    """Raised when a symbol is invalid or unsupported by the provider."""

    code = "invalid_symbol"


class RateLimitError(MarketDataError):
    """Raised when a provider rate limit blocks a request."""

    code = "rate_limited"


class MalformedMarketDataError(MarketDataError):
    """Raised when provider data is missing required fields or has bad shape."""

    code = "malformed_market_data"


__all__ = [
    "InvalidSymbolError",
    "MalformedMarketDataError",
    "MarketDataError",
    "ProviderUnavailableError",
    "RateLimitError",
]
