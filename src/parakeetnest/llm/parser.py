"""Strict JSON output parsing for LLM responses."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from parakeetnest.committee.models import ChairmanSummary, CommitteeOpinion
from parakeetnest.llm.models import JSONSchema, LLMResponse
from parakeetnest.llm.schemas import (
    CHAIRMAN_SUMMARY_SCHEMA,
    COMMITTEE_OPINION_SCHEMA,
    DAILY_REPORT_SCHEMA,
)
from parakeetnest.models import (
    ConfidenceLevel,
    EvidenceItem,
    InvestmentHorizon,
    RecommendationAction,
)


@dataclass(frozen=True)
class OutputParserError(ValueError):
    """Raised when model output fails strict JSON validation."""

    message: str

    def __str__(self) -> str:
        return self.message


class OutputParser:
    """Parse model JSON into typed committee outputs."""

    def parse_json(self, response: LLMResponse, schema: JSONSchema) -> dict[str, Any]:
        """Decode and validate a JSON object against a supported schema subset."""
        if not response.ok:
            code = response.error.code if response.error else response.finish_reason
            raise OutputParserError(f"LLM response failed before parsing: {code}")
        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise OutputParserError(f"Invalid JSON output: {exc.msg}") from exc
        self._validate(payload, schema, "$")
        return payload

    def parse_committee_opinion(self, response: LLMResponse) -> CommitteeOpinion:
        """Parse a committee member opinion from an LLM response."""
        payload = self.parse_json(response, COMMITTEE_OPINION_SCHEMA)
        return CommitteeOpinion(
            member_name=payload["member_name"],
            role=payload["role"],
            symbol=payload["symbol"],
            viewpoint=payload["viewpoint"],
            confidence=ConfidenceLevel(payload["confidence"]),
            evidence=self._evidence_items(payload["evidence"]),
            risks=tuple(payload["risks"]),
            catalysts=tuple(payload["catalysts"]),
        )

    def parse_chairman_summary(self, response: LLMResponse) -> ChairmanSummary:
        """Parse a Chairman summary from an LLM response."""
        payload = self.parse_json(response, CHAIRMAN_SUMMARY_SCHEMA)
        return ChairmanSummary(
            symbol=payload["symbol"],
            action=RecommendationAction(payload["action"]),
            confidence=ConfidenceLevel(payload["confidence"]),
            horizon=InvestmentHorizon(payload["horizon"]),
            rationale=payload["rationale"],
            evidence=self._evidence_items(payload["evidence"]),
            risks=tuple(payload["risks"]),
            catalysts=tuple(payload["catalysts"]),
            data_confidence=ConfidenceLevel(payload["data_confidence"]),
        )

    def parse_daily_report(self, response: LLMResponse) -> dict[str, Any]:
        """Parse a daily report JSON object."""
        return self.parse_json(response, DAILY_REPORT_SCHEMA)

    def _validate(self, value: Any, schema: JSONSchema, path: str) -> None:
        expected_type = schema.get("type")
        if expected_type and not self._matches_type(value, expected_type):
            raise OutputParserError(f"{path} expected {expected_type}")
        if isinstance(value, Mapping):
            self._validate_object(value, schema, path)
        if isinstance(value, list):
            self._validate_array(value, schema, path)
        enum_values = schema.get("enum")
        if enum_values is not None and value not in enum_values:
            raise OutputParserError(f"{path} must be one of {enum_values}")
        min_length = schema.get("minLength")
        if min_length is not None and isinstance(value, str) and len(value) < min_length:
            raise OutputParserError(f"{path} must not be empty")

    def _validate_object(self, value: Mapping[str, Any], schema: JSONSchema, path: str) -> None:
        required = set(schema.get("required", ()))
        missing = sorted(required.difference(value))
        if missing:
            raise OutputParserError(f"{path} missing required fields: {', '.join(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value).difference(properties))
            if extra:
                raise OutputParserError(f"{path} has unsupported fields: {', '.join(extra)}")
        for key, item in value.items():
            item_schema = properties.get(key)
            if item_schema is not None:
                self._validate(item, item_schema, f"{path}.{key}")

    def _validate_array(self, value: list[Any], schema: JSONSchema, path: str) -> None:
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            raise OutputParserError(f"{path} must contain at least {min_items} items")
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                self._validate(item, item_schema, f"{path}[{index}]")

    @staticmethod
    def _matches_type(value: Any, expected_type: Any) -> bool:
        if isinstance(expected_type, list):
            return any(OutputParser._matches_type(value, item) for item in expected_type)
        if expected_type == "object":
            return isinstance(value, Mapping)
        if expected_type == "array":
            return isinstance(value, list)
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "null":
            return value is None
        return True

    @staticmethod
    def _evidence_items(items: list[dict[str, Any]]) -> tuple[EvidenceItem, ...]:
        return tuple(
            EvidenceItem(
                summary=item["summary"],
                source=item["source"],
                observed_at=OutputParser._parse_datetime(item.get("observed_at")),
            )
            for item in items
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise OutputParserError("observed_at must be an ISO datetime") from exc
