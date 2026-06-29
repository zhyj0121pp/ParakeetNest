"""Common custom exceptions for ParakeetNest."""


class ParakeetNestError(Exception):
    """Base exception for all project-specific errors."""


class ConfigurationError(ParakeetNestError):
    """Raised when application configuration is invalid or incomplete."""


class DataValidationError(ParakeetNestError):
    """Raised when input data fails validation before analysis."""


class ExternalServiceNotConfiguredError(ParakeetNestError):
    """Raised when a future external integration lacks required settings."""


class RecommendationError(ParakeetNestError):
    """Raised when a recommendation cannot satisfy the required contract."""
