"""Data quality models and validation placeholders."""

from dataclasses import dataclass, field
from datetime import datetime

from parakeetnest.models import ConfidenceLevel


@dataclass(frozen=True)
class DataQualityReport:
    """Describe source freshness, missing fields, and validation state."""

    source: str
    fetched_at: datetime | None
    is_valid: bool
    missing_fields: tuple[str, ...] = field(default_factory=tuple)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW


class DataQualityValidator:
    """Validate datasets before analysis services consume them."""

    def validate(self, source: str, required_fields: tuple[str, ...]) -> DataQualityReport:
        """Return a conservative placeholder validation report."""
        return DataQualityReport(
            source=source,
            fetched_at=None,
            is_valid=False,
            missing_fields=required_fields,
        )
