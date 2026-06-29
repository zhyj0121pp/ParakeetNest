"""Application bootstrap for ParakeetNest."""

from dataclasses import dataclass

from parakeetnest.config import Settings, get_settings
from parakeetnest.logging import configure_logging, get_logger


@dataclass(frozen=True)
class ApplicationRuntime:
    """Container for application-wide runtime dependencies."""

    settings: Settings


def bootstrap(settings: Settings | None = None) -> ApplicationRuntime:
    """Initialize foundational application services and return the runtime."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    logger = get_logger(__name__)
    logger.info(
        "Application bootstrap complete",
        extra={"environment": resolved_settings.environment},
    )
    return ApplicationRuntime(settings=resolved_settings)
