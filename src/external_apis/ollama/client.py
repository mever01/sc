"""Ollama API HTTP client."""

import logging
from typing import Any

import httpx

from src.config.ollama import ollama_settings
from .errors import OllamaConnectionError, OllamaResponseError
from .schemas import OllamaGenerateResponse, OllamaModelInfo

logger = logging.getLogger(__name__)


class OllamaApiClient:
    """HTTP client for interacting with local or remote Ollama server."""

    def __init__(
        self,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        raw_url = (base_url or ollama_settings.resolved_base_url).strip().rstrip("/")
        if "/api" in raw_url:
            raw_url = raw_url.split("/api")[0]
        self.base_url = raw_url

        self.default_model = (default_model or ollama_settings.model).strip()
        self.timeout = timeout if timeout is not None else ollama_settings.timeout

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )

    def is_online(self, timeout: float = 2.0) -> bool:
        """Check if Ollama service is reachable."""
        try:
            res = self._client.get("/api/ps", timeout=timeout)
            return res.status_code == 200
        except Exception:
            return False

    def get_running_models(self) -> list[OllamaModelInfo]:
        """Return list of models currently loaded in Ollama VRAM."""
        try:
            res = self._client.get("/api/ps")
            res.raise_for_status()
            models_data = res.json().get("models", [])
            return [
                OllamaModelInfo(
                    name=m.get("name", ""),
                    model=m.get("model"),
                    size=m.get("size"),
                    digest=m.get("digest"),
                )
                for m in models_data
            ]
        except httpx.RequestError as exc:
            logger.debug("Failed to connect to Ollama /api/ps: %s", exc)
            raise OllamaConnectionError(f"Ollama connection failed: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaResponseError(f"HTTP {exc.response.status_code}: {exc.response.text}") from exc

    def generate(
        self,
        prompt: str,
        images: list[str] | None = None,
        model: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> OllamaGenerateResponse:
        """Send a generation request to /api/generate."""
        target_model = model or self.default_model
        payload: dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
        }
        if images:
            payload["images"] = images
        if options:
            payload["options"] = options

        try:
            res = self._client.post("/api/generate", json=payload)
            res.raise_for_status()
            data = res.json()
            return OllamaGenerateResponse(
                response=data.get("response", ""),
                done=data.get("done", True),
                total_duration=data.get("total_duration"),
            )
        except httpx.RequestError as exc:
            logger.warning("Ollama connection error during generate: %s", exc)
            raise OllamaConnectionError(f"Ollama connection error: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("Ollama HTTP %d error: %s", exc.response.status_code, exc.response.text)
            raise OllamaResponseError(
                f"Ollama HTTP {exc.response.status_code}: {exc.response.text}"
            ) from exc

    def close(self) -> None:
        """Close underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
