"""Exceptions for Ollama API client."""


class OllamaError(Exception):
    """Base exception for Ollama API errors."""


class OllamaConnectionError(OllamaError):
    """Raised when Ollama service is unreachable."""


class OllamaResponseError(OllamaError):
    """Raised when Ollama returns an error or non-200 response."""
