"""
tests/test_formatter.py
Unit tests for formatter.py — terminal display and Markdown/JSON exports.
No real LLM calls; everything runs on fixture ChunkAnalysis objects.
"""
import json

import pytest

from src.analyzer import ChunkAnalysis
from src.formatter import display_analyses, export_markdown, export_json


@pytest.fixture
def analysis_with_incidents() -> ChunkAnalysis:
    return ChunkAnalysis.model_validate(
        {
            "summary": "Critical payment incident, then a temporary DB outage auto-recovered.",
            "incidents": [
                {
                    "severity": "CRITICAL",
                    "title": "Payment service unavailable",
                    "root_cause": "Repeated timeouts to the external service, circuit breaker opened",
                    "affected_module": "payment",
                    "suggested_fix": "Check external service health, raise timeout to 60s",
                    "related_lines": [4, 5, 6, 7, 8],
                },
                {
                    "severity": "ERROR",
                    "title": "User account locked",
                    "root_cause": "3 consecutive failed login attempts for jdupont",
                    "affected_module": "auth",
                    "suggested_fix": "Add a captcha after 2 failed attempts",
                    "related_lines": [9, 10, 11, 12],
                },
            ],
        }
    )


@pytest.fixture
def analysis_without_incidents() -> ChunkAnalysis:
    return ChunkAnalysis.model_validate({"summary": "Nothing unusual, all INFO logs.", "incidents": []})


# ---------------------------------------------------------------------------
# display_analyses (smoke tests — just make sure it doesn't crash)
# ---------------------------------------------------------------------------

def test_display_analyses_with_incidents_does_not_raise(analysis_with_incidents):
    display_analyses([analysis_with_incidents], "logs/sample.log")


def test_display_analyses_without_incidents_does_not_raise(analysis_without_incidents):
    display_analyses([analysis_without_incidents], "logs/sample.log")


# ---------------------------------------------------------------------------
# export_markdown
# ---------------------------------------------------------------------------

def test_export_markdown_creates_file_with_expected_content(tmp_path, analysis_with_incidents):
    output_path = export_markdown([analysis_with_incidents], "logs/sample.log", output_dir=str(tmp_path))

    assert output_path.exists()
    assert output_path.suffix == ".md"

    content = output_path.read_text(encoding="utf-8")
    assert "logs/sample.log" in content
    assert "Payment service unavailable" in content
    assert "CRITICAL" in content
    assert "| Severity | Title | Module | Root cause | Fix | Lines |" in content


def test_export_markdown_without_incidents_says_so(tmp_path, analysis_without_incidents):
    output_path = export_markdown([analysis_without_incidents], "logs/sample.log", output_dir=str(tmp_path))
    content = output_path.read_text(encoding="utf-8")
    assert "No incident detected" in content


# ---------------------------------------------------------------------------
# export_json
# ---------------------------------------------------------------------------

def test_export_json_creates_valid_json_file(tmp_path, analysis_with_incidents):
    output_path = export_json([analysis_with_incidents], "logs/sample.log", output_dir=str(tmp_path))

    assert output_path.exists()
    assert output_path.suffix == ".json"

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["log_file"] == "logs/sample.log"
    assert "generated_at" in data
    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["incidents"][0]["title"] == "Payment service unavailable"
    assert data["chunks"][0]["incidents"][0]["severity"] == "CRITICAL"


def test_export_json_without_incidents_has_empty_list(tmp_path, analysis_without_incidents):
    output_path = export_json([analysis_without_incidents], "logs/sample.log", output_dir=str(tmp_path))
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["chunks"][0]["incidents"] == []