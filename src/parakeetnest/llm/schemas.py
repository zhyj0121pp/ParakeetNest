"""JSON schemas for model-generated committee and report outputs."""

from __future__ import annotations

from parakeetnest.llm.models import JSONSchema
from parakeetnest.models import ConfidenceLevel, InvestmentHorizon, RecommendationAction


EVIDENCE_ITEM_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "source"],
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "source": {"type": "string", "minLength": 1},
        "observed_at": {"type": ["string", "null"]},
    },
}

COMMITTEE_OPINION_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "member_name",
        "role",
        "symbol",
        "viewpoint",
        "confidence",
        "evidence",
        "risks",
        "catalysts",
    ],
    "properties": {
        "member_name": {"type": "string", "minLength": 1},
        "role": {"type": "string", "minLength": 1},
        "symbol": {"type": "string", "minLength": 1},
        "viewpoint": {"type": "string", "minLength": 1},
        "confidence": {"type": "string", "enum": [level.value for level in ConfidenceLevel]},
        "evidence": {"type": "array", "items": EVIDENCE_ITEM_SCHEMA},
        "risks": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "catalysts": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
}

PORTFOLIO_COMMITTEE_OBSERVATION_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "agent_name",
        "role",
        "portfolio_view",
        "advisory_action",
        "confidence",
        "horizon",
        "evidence",
        "risks",
        "catalysts",
    ],
    "properties": {
        "agent_name": {"type": "string", "minLength": 1},
        "role": {"type": "string", "minLength": 1},
        "portfolio_view": {"type": "string", "minLength": 1},
        "advisory_action": {"type": "string", "minLength": 1},
        "confidence": {"type": "string", "enum": [level.value for level in ConfidenceLevel]},
        "horizon": {"type": "string", "enum": [horizon.value for horizon in InvestmentHorizon]},
        "evidence": {"type": "array", "items": EVIDENCE_ITEM_SCHEMA},
        "risks": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "catalysts": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
}

CHAIRMAN_SUMMARY_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "symbol",
        "action",
        "confidence",
        "horizon",
        "rationale",
        "evidence",
        "risks",
        "catalysts",
        "data_confidence",
    ],
    "properties": {
        "symbol": {"type": "string", "minLength": 1},
        "action": {"type": "string", "enum": [action.value for action in RecommendationAction]},
        "confidence": {"type": "string", "enum": [level.value for level in ConfidenceLevel]},
        "horizon": {"type": "string", "enum": [horizon.value for horizon in InvestmentHorizon]},
        "rationale": {"type": "string", "minLength": 1},
        "evidence": {"type": "array", "items": EVIDENCE_ITEM_SCHEMA},
        "risks": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "catalysts": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "data_confidence": {
            "type": "string",
            "enum": [level.value for level in ConfidenceLevel],
        },
    },
}

DAILY_REPORT_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "report_date",
        "portfolio_summary",
        "market_summary",
        "committee_opinions",
        "chairman_summary",
        "recommendations",
        "risks",
        "catalysts",
    ],
    "properties": {
        "report_date": {"type": "string", "minLength": 1},
        "portfolio_summary": {"type": "string", "minLength": 1},
        "market_summary": {"type": "string", "minLength": 1},
        "committee_opinions": {"type": "array", "items": COMMITTEE_OPINION_SCHEMA},
        "chairman_summary": CHAIRMAN_SUMMARY_SCHEMA,
        "recommendations": {
            "type": "array",
            "items": CHAIRMAN_SUMMARY_SCHEMA,
            "minItems": 1,
        },
        "risks": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "catalysts": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
}

SCHEMAS: dict[str, JSONSchema] = {
    "CommitteeOpinion": COMMITTEE_OPINION_SCHEMA,
    "PortfolioCommitteeObservation": PORTFOLIO_COMMITTEE_OBSERVATION_SCHEMA,
    "ChairmanSummary": CHAIRMAN_SUMMARY_SCHEMA,
    "DailyReport": DAILY_REPORT_SCHEMA,
}
