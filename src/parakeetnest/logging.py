"""Structured logging setup for ParakeetNest."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import logging as stdlib_logging
from typing import Any

from parakeetnest.config import Settings


_STANDARD_RECORD_FIELDS = set(stdlib_logging.makeLogRecord({}).__dict__)


class JsonFormatter(stdlib_logging.Formatter):
    """Format log records as compact JSON objects."""

    def format(self, record: stdlib_logging.LogRecord) -> str:
        """Return a structured JSON representation of a log record."""
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_FIELDS
        }
        payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_logging(settings: Settings) -> None:
    """Configure root logging for the application runtime."""
    handler = stdlib_logging.StreamHandler()
    formatter: stdlib_logging.Formatter
    if settings.log_json:
        formatter = JsonFormatter()
    else:
        formatter = stdlib_logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    handler.setFormatter(formatter)

    root_logger = stdlib_logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)


def get_logger(name: str) -> stdlib_logging.Logger:
    """Return a named logger."""
    return stdlib_logging.getLogger(name)
