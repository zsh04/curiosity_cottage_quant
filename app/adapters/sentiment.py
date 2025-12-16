from typing import Dict, Any
import requests
import time
import logging
import os

logger = logging.getLogger(__name__)


class SentimentAdapter:
    """Wrapper for FinBERT with full observability"""

    def __init__(self):
        self.finbert_url = os.getenv("FINBERT_API_URL", "http://cc_finbert:8000")

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Get sentiment analysis from FinBERT with latency tracking.

        Returns:
            dict with keys: label, score, latency_ms, input_text, error (optional)
        """
        start = time.time()

        try:
            resp = requests.post(
                f"{self.finbert_url}/analyze", json={"text": text}, timeout=5
            )
            resp.raise_for_status()
            data = resp.json()

            latency_ms = (time.time() - start) * 1000

            return {
                "label": data.get("label", "neutral"),
                "score": data.get("score", 0.0),
                "latency_ms": latency_ms,
                "input_text": text[:100],  # Store truncated input for audit
            }

        except Exception as e:
            logger.error(f"FinBERT Error: {e}")
            latency_ms = (time.time() - start) * 1000

            return {
                "label": "error",
                "score": 0.0,
                "latency_ms": latency_ms,
                "input_text": text[:100],
                "error": str(e),
            }
