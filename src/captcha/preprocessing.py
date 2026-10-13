"""OpenCV preprocessing for captcha images."""

import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def preprocess_captcha(raw_bytes: bytes) -> bytes:
    """Denoise captcha image with Otsu thresholding + median filter."""
    try:
        arr = np.frombuffer(raw_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        clean = cv2.medianBlur(thresh, 3)
        _, encoded = cv2.imencode(".png", clean)
        return encoded.tobytes()
    except Exception as exc:
        logger.debug("OpenCV pre-processing failed: %s", exc)
        return raw_bytes
