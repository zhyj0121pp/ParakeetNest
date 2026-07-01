"""Provider-neutral portfolio provider exceptions."""

from __future__ import annotations


class PortfolioProviderError(Exception):
    """Base class for provider-independent portfolio data failures."""


class PortfolioAccountNotFoundError(PortfolioProviderError):
    """Raised when a portfolio account id is not available from a provider."""


class PortfolioDataUnavailableError(PortfolioProviderError):
    """Raised when portfolio data cannot be retrieved for a known account."""


__all__ = [
    "PortfolioAccountNotFoundError",
    "PortfolioDataUnavailableError",
    "PortfolioProviderError",
]
