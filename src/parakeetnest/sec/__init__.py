"""Provider-agnostic SEC Filing Layer interfaces and domain models."""

from parakeetnest.sec.edgar import EdgarSecFilingProvider, SECEDGARProvider
from parakeetnest.sec.mock import MockSecFilingProvider
from parakeetnest.sec.models import (
    FilingType,
    SecFiling,
    SecFilingContent,
    SecFilingQuery,
)
from parakeetnest.sec.provider import (
    ProviderError,
    SecFilingError,
    SecFilingHttpError,
    SecFilingParsingError,
    SecFilingProvider,
)
from parakeetnest.sec.registry import (
    SecFilingProviderRegistration,
    SecFilingProviderRegistry,
    create_sec_filing_provider_registry,
)
from parakeetnest.sec.service import SecFilingService

__all__ = [
    "FilingType",
    "EdgarSecFilingProvider",
    "SECEDGARProvider",
    "MockSecFilingProvider",
    "ProviderError",
    "SecFiling",
    "SecFilingContent",
    "SecFilingError",
    "SecFilingHttpError",
    "SecFilingParsingError",
    "SecFilingProviderRegistration",
    "SecFilingProviderRegistry",
    "SecFilingProvider",
    "SecFilingQuery",
    "SecFilingService",
    "create_sec_filing_provider_registry",
]
