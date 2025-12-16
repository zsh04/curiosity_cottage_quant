"""
FinBERT Sentiment Analysis Adapter
Connects to cc_finbert microservice for financial sentiment classification.
"""

import logging
import os
from typing import Dict, Any, List, Union

import requests
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class SentimentAdapter:
    """
    Client for FinBERT financial sentiment analysis microservice.

    FinBERT provides:
        - Financial domain-specific sentiment classification
        - Labels: positive, negative, neutral
        - Confidence scores for each prediction
    """

    def __init__(self, base_url: str = None):
        """
        Initialize sentiment adapter.

        Args:
            base_url: FinBERT service URL (defaults to env FINBERT_URL or http://cc_finbert:8000)
        """
        # Use FINBERT_URL from config, fallback to env, then default
        from app.core.config import settings

        self.base_url = (
            base_url
            or getattr(settings, "FINBERT_URL", None)
            or os.getenv("FINBERT_URL", "http://cc_finbert:8000")
        )
        self.timeout = 2.0  # 2-second timeout

    @tracer.start_as_current_span("finbert_analyze")
    def analyze(self, text: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Analyze sentiment using FinBERT.

        Args:
            text: Single text string or list of texts for batch processing

        Returns:
            Dict with keys:
                - sentiment: "positive" | "negative" | "neutral"
                - score: float confidence (0.0-1.0)
                - label: legacy alias for sentiment
                - latency_ms: response time
                - error: optional error message if offline
        """
        span = trace.get_current_span()

        # Handle batch vs single automatically
        is_batch = isinstance(text, list)
        texts_to_analyze = text if is_batch else [text]

        span.set_attribute("finbert.batch", is_batch)
        span.set_attribute("finbert.count", len(texts_to_analyze))

        try:
            # Construct payload (FinBERT expects {"text": str or List[str]})
            payload = {"text": text}

            # POST to /analyze endpoint (FinBERT service main.py)
            response = requests.post(
                f"{self.base_url}/analyze",
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                logger.error(
                    f"FinBERT error: HTTP {response.status_code} - {response.text}"
                )
                span.set_attribute("error", True)
                return self._fallback_response("http_error")

            # Parse response
            data = response.json()

            # Standardize output format
            result = {
                "sentiment": data.get("label", "neutral").lower(),
                "label": data.get("label", "neutral"),  # Legacy compatibility
                "score": float(data.get("score", 0.0)),
                "latency_ms": data.get("latency_ms", 0),
            }

            logger.debug(f"📊 FinBERT: {result['sentiment']} ({result['score']:.2f})")

            span.set_attribute("finbert.sentiment", result["sentiment"])
            span.set_attribute("finbert.score", result["score"])

            return result

        except requests.Timeout:
            logger.warning(f"⏱️  FinBERT timeout after {self.timeout}s")
            span.set_attribute("error.timeout", True)
            return self._fallback_response("timeout")

        except requests.ConnectionError:
            logger.warning("🔌 FinBERT service unreachable (cc_finbert down?)")
            span.set_attribute("error.connection", True)
            return self._fallback_response("offline")

        except Exception as e:
            logger.error(f"FinBERT adapter error: {e}")
            span.set_attribute("error", True)
            return self._fallback_response(str(e))

    def _fallback_response(self, error_msg: str) -> Dict[str, Any]:
        """
        Return safe fallback when service is unavailable.
        Prevents trading loop crashes.

        Args:
            error_msg: Error description

        Returns:
            Neutral sentiment with error indicator
        """
        return {
            "sentiment": "neutral",
            "label": "neutral",
            "score": 0.0,
            "latency_ms": 0,
            "error": error_msg,
        }

    def health_check(self) -> bool:
        """
        Check if FinBERT service is healthy.

        Returns:
            True if service responds to /health, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=1.0)
            return response.status_code == 200
        except Exception:
            return False
