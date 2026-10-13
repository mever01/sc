"""Captcha solving via local Ollama vision model."""

import base64
import logging

from src.config.ollama import ollama_settings
from src.external_apis.ollama import OllamaApiClient, OllamaError

logger = logging.getLogger(__name__)


def solve_via_ollama(img_bytes: bytes, expected_length: int = 6) -> str | None:
    """Solve captcha using Ollama vision model.

    Encodes image to base64, prompts Ollama, and validates extracted code.
    Returns 6-char alphanumeric code or None if solving failed.
    """
    if not ollama_settings.enabled:
        return None

    b64_img = base64.b64encode(img_bytes).decode()
    prompt = (
        f"This captcha image contains exactly {expected_length} alphanumeric characters. "
        f"Output ONLY these {expected_length} characters without spaces, quotes, or punctuation."
    )
    options = {"num_predict": 20, "temperature": 0.0}

    try:
        with OllamaApiClient() as client:
            result = client.generate(
                prompt=prompt,
                images=[b64_img],
                options=options,
            )

        raw = result.response.strip()
        code = "".join(c for c in raw if c.isalnum())

        if len(code) == expected_length:
            logger.info("Ollama solved captcha: %r", code)
            return code
        if len(code) > expected_length:
            trimmed = code[:expected_length]
            logger.info("Ollama returned %r, trimmed to %r", code, trimmed)
            return trimmed

        logger.warning(
            "Ollama response %r filtered to %r (length %d != %d), discarding",
            raw,
            code,
            len(code),
            expected_length,
        )
        return None
    except OllamaError as exc:
        logger.warning("Ollama captcha solving failed: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Unexpected error during Ollama captcha solving: %s", exc)
        return None
