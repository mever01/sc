"""Captcha solving via ddddocr with OpenCV denoising."""

import logging

import ddddocr

from .preprocessing import preprocess_captcha

logger = logging.getLogger(__name__)


class DdddocrSolver:
    """Encapsulates ddddocr base and beta models."""

    def __init__(self) -> None:
        self._ocr = ddddocr.DdddOcr(show_ad=False)
        try:
            self._ocr_beta = ddddocr.DdddOcr(beta=True, show_ad=False)
        except Exception:
            self._ocr_beta = None

    def solve(self, raw_bytes: bytes) -> str | None:
        """Try raw, denoised, and beta variants; return best 6-character candidate."""
        clean_bytes = preprocess_captcha(raw_bytes)

        pred_raw = "".join(c for c in self._ocr.classification(raw_bytes) if c.isalnum())
        pred_clean = "".join(c for c in self._ocr.classification(clean_bytes) if c.isalnum())
        pred_beta = (
            "".join(c for c in self._ocr_beta.classification(clean_bytes) if c.isalnum())
            if self._ocr_beta
            else ""
        )

        logger.debug(
            "ddddocr variants — raw=%r, clean=%r, beta=%r",
            pred_raw,
            pred_clean,
            pred_beta,
        )

        candidates = [pred_clean, pred_beta, pred_raw]

        exact = [p for p in candidates if len(p) == 6]
        if exact:
            return exact[0]

        long_enough = [p for p in candidates if len(p) >= 4]
        if long_enough:
            return long_enough[0][:6]

        fallback = pred_clean or pred_raw
        return fallback[:6] if fallback else None
