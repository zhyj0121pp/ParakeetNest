"""Provider-agnostic Macro Layer domain models."""

from parakeetnest.macro.models import (
    MacroCategory,
    MacroFrequency,
    MacroIndicator,
    MacroObservation,
    MacroSeries,
    MacroSnapshot,
    MacroUnit,
)
from parakeetnest.macro.fred import FREDMacroProvider
from parakeetnest.macro.mock import MockMacroDataProvider
from parakeetnest.macro.provider import (
    MacroDataConfigurationError,
    MacroDataError,
    MacroDataHttpError,
    MacroDataParsingError,
    MacroDataProvider,
)
from parakeetnest.macro.registry import (
    MacroDataProviderRegistration,
    MacroDataProviderRegistry,
    create_macro_data_provider_registry,
)
from parakeetnest.macro.service import MacroDataService

__all__ = [
    "FREDMacroProvider",
    "MacroCategory",
    "MacroDataConfigurationError",
    "MacroDataError",
    "MacroDataHttpError",
    "MacroDataParsingError",
    "MacroDataProvider",
    "MacroDataProviderRegistration",
    "MacroDataProviderRegistry",
    "MacroDataService",
    "MacroFrequency",
    "MacroIndicator",
    "MacroObservation",
    "MacroSeries",
    "MacroSnapshot",
    "MacroUnit",
    "MockMacroDataProvider",
    "create_macro_data_provider_registry",
]
