"""
LLM calls (Gemini / OpenAI / Anthropic) to analyze a log chunk,
with strict output validation via Pydantic.
"""
import json
import os
from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field

from src.parser import LogChunk


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Incident(BaseModel):
    severity: Severity = Field(description="Overall severity level of the detected incident")
    title: str = Field(description="Short title of the incident")
    root_cause: str = Field(description="Explanation of the likely root cause")
    affected_module: str | None = Field(default=None, description="Affected module/service")
    suggested_fix: str = Field(description="Recommended fix or action")
    related_lines: list[int] = Field(default_factory=list, description="Line numbers in the log related to this incident")


class ChunkAnalysis(BaseModel):
    summary: str = Field(description="Synthetic summary of what's happening in this log chunk")
    incidents: list[Incident] = Field(default_factory=list, description="List of detected incidents")


ANALYSIS_JSON_SCHEMA = ChunkAnalysis.model_json_schema()

SYSTEM_PROMPT = """You are an expert SRE engineer specialized in production log analysis.
Analyze the provided log fragment and respond ONLY with valid JSON matching
the requested schema. Be precise and concise, and only mention what is visible
in the provided logs. If everything looks fine (only INFO/DEBUG), return an
empty incidents list."""


# ---------------------------------------------------------------------------
# Abstract provider interface
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Common interface implemented by all LLM providers."""

    @abstractmethod
    def analyze_chunk(self, chunk: LogChunk) -> ChunkAnalysis:
        ...


def _build_user_prompt(chunk: LogChunk) -> str:
    return (
        f"Log fragment (lines {chunk.start_line} to {chunk.end_line}):\n\n"
        f"{chunk.to_text()}\n\n"
        f"Expected JSON schema:\n{json.dumps(ANALYSIS_JSON_SCHEMA, ensure_ascii=False)}"
    )


# ---------------------------------------------------------------------------
# Gemini provider (implemented first — free tier)
# ---------------------------------------------------------------------------

class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-3.6-flash"):
        from google import genai  # local import so the SDK isn't required if unused

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY missing from environment (.env)")

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def analyze_chunk(self, chunk: LogChunk) -> ChunkAnalysis:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=_build_user_prompt(chunk),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ChunkAnalysis,
            ),
        )
        return ChunkAnalysis.model_validate_json(response.text)


# ---------------------------------------------------------------------------
# OpenAI provider (stub, ready to activate)
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o-mini"):
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY missing from environment (.env)")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def analyze_chunk(self, chunk: LogChunk) -> ChunkAnalysis:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(chunk)},
            ],
            response_format={"type": "json_object"},
        )
        return ChunkAnalysis.model_validate_json(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Anthropic provider (stub, ready to activate)
# ---------------------------------------------------------------------------

class AnthropicProvider(LLMProvider):
    def __init__(self, model: str = "claude-3-5-sonnet-latest"):
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing from environment (.env)")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def analyze_chunk(self, chunk: LogChunk) -> ChunkAnalysis:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(chunk)}],
        )
        text = message.content[0].text
        # Strip potential ```json ... ``` wrapping from the model's response
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return ChunkAnalysis.model_validate_json(text)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

PROVIDER_MODELS = {
    "gemini-3.6-flash": GeminiProvider,
    "gpt-4o-mini": OpenAIProvider,
    "gpt-4o": OpenAIProvider,
    "claude-3-5-sonnet": AnthropicProvider,
}


def get_provider(model: str) -> LLMProvider:
    provider_cls = PROVIDER_MODELS.get(model)
    if provider_cls is None:
        raise ValueError(
            f"Unknown model: {model}. Available models: {', '.join(PROVIDER_MODELS)}"
        )
    return provider_cls(model=model)