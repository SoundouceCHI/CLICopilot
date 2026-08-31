"""
Unit tests for analyzer.py — schema validation and provider factory,
without making real LLM API calls.
"""
import pytest
from pydantic import ValidationError

from src.analyzer import (
    ChunkAnalysis,
    Incident,
    Severity,
    ANALYSIS_JSON_SCHEMA,
    get_provider,
    GeminiProvider,
    OpenAIProvider,
    AnthropicProvider,
)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_valid_chunk_analysis_parses_correctly():
    data = {
        "summary": "Critical payment incident detected",
        "incidents": [
            {
                "severity": "CRITICAL",
                "title": "Payment service unavailable",
                "root_cause": "Repeated timeouts, circuit breaker opened",
                "affected_module": "payment",
                "suggested_fix": "Check external service health, raise timeout",
                "related_lines": [4, 5, 6],
            }
        ],
    }
    analysis = ChunkAnalysis.model_validate(data)

    assert analysis.summary == "Critical payment incident detected"
    assert len(analysis.incidents) == 1
    assert analysis.incidents[0].severity == Severity.CRITICAL
    assert analysis.incidents[0].related_lines == [4, 5, 6]


def test_empty_incidents_list_is_valid():
    analysis = ChunkAnalysis.model_validate({"summary": "Everything is fine", "incidents": []})
    assert analysis.incidents == []


def test_invalid_severity_raises_validation_error():
    bad_data = {
        "summary": "x",
        "incidents": [
            {
                "severity": "NOT_A_LEVEL",
                "title": "t",
                "root_cause": "r",
                "suggested_fix": "f",
            }
        ],
    }
    with pytest.raises(ValidationError):
        ChunkAnalysis.model_validate(bad_data)


def test_missing_required_field_raises_validation_error():
    incomplete = {"summary": "x", "incidents": [{"severity": "ERROR", "title": "t"}]}
    with pytest.raises(ValidationError):
        ChunkAnalysis.model_validate(incomplete)


def test_affected_module_is_optional():
    incident = Incident(
        severity=Severity.WARN,
        title="High cache miss ratio",
        root_cause="Cache warmup incomplete",
        suggested_fix="Pre-warm cache on deploy",
    )
    assert incident.affected_module is None


def test_json_schema_contains_expected_definitions():
    defs = ANALYSIS_JSON_SCHEMA.get("$defs", {})
    assert "Incident" in defs
    assert "Severity" in defs


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def test_get_provider_unknown_model_raises_value_error():
    with pytest.raises(ValueError):
        get_provider("not-a-real-model")


def test_get_provider_maps_to_correct_class(monkeypatch):
    # Avoid real client instantiation by stubbing out the API key checks
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    assert isinstance(get_provider("gemini-2.0-flash"), GeminiProvider)
    assert isinstance(get_provider("gpt-4o-mini"), OpenAIProvider)
    assert isinstance(get_provider("claude-3-5-sonnet"), AnthropicProvider)


def test_provider_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        GeminiProvider()