"""Data schemas for Ollama API."""

from dataclasses import dataclass


@dataclass
class OllamaModelInfo:
    name: str
    model: str | None = None
    size: int | None = None
    digest: str | None = None


@dataclass
class OllamaGenerateResponse:
    response: str
    done: bool = True
    total_duration: int | None = None
