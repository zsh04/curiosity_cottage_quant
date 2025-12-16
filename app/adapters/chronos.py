"""
Chronos-2 Time-Series Forecasting Adapter
Connects cc_engine to cc_chronos microservice for probabilistic forecasts.
"""

import logging
import os
from typing import Dict, List, Optional

import requests
import numpy as np
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class ChronosAdapter:
    """
    Client for Chronos-2 Time-Series Forecasting microservice.

    Chronos-2 (amazon/chronos-t5-small) provides:
        - Probabilistic forecasts with quantiles (10th, 50th, 90th)
        - Zero-shot inference (no fine-tuning needed)
        - Handles irregular time-series
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Chronos adapter.

        Args:
            base_url: Chronos service URL (defaults to env CHRONOS_URL or http://cc_chronos:8002)
        """
        self.base_url = base_url or os.getenv("CHRONOS_URL", "http://cc_chronos:8002")
        self.timeout = 10.0  # 10-second timeout

    @tracer.start_as_current_span("chronos_predict")
    def predict(
        self, prices: List[float], horizon: int = 10
    ) -> Optional[Dict[str, List[float]]]:
        """
        Generate probabilistic forecast using Chronos-2.

        Args:
            prices: Historical price context (last N observations)
            horizon: Number of steps to forecast ahead

        Returns:
            Dict with keys:
                - median: List[float] (50th percentile forecast)
                - low: List[float] (10th percentile - bearish scenario)
                - high: List[float] (90th percentile - bullish scenario)
            Returns None if service is unreachable or errors occur.
        """
        span = trace.get_current_span()
        span.set_attribute("chronos.context_length", len(prices))
        span.set_attribute("chronos.horizon", horizon)

        if len(prices) < 10:
            logger.warning("Chronos: Insufficient context (need ≥10 points)")
            return None

        try:
            # Format payload
            payload = {"context": prices, "prediction_length": horizon}

            # POST to microservice
            response = requests.post(
                f"{self.base_url}/forecast",
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                logger.error(
                    f"Chronos error: HTTP {response.status_code} - {response.text}"
                )
                span.set_attribute("error", True)
                return None

            # Parse response
            data = response.json()

            # Handle raw samples format (from Chronos service v2)
            if "forecast" in data and isinstance(data["forecast"], list):
                samples = np.array(data["forecast"])  # Shape: (samples, horizon)
                # Calculate quantiles along axis 0 (across samples)
                median = np.quantile(samples, 0.5, axis=0).tolist()
                low = np.quantile(samples, 0.1, axis=0).tolist()
                high = np.quantile(samples, 0.9, axis=0).tolist()

                forecast = {
                    "median": median,
                    "low": low,
                    "high": high,
                }
            else:
                # Handle formatted (legacy/mock) response
                if not data.get("median"):
                    logger.error(f"⚠️ Chronos returned empty forecast. Response: {data}")

                forecast = {
                    "median": data.get("median", []),
                    "low": data.get("quantile_0.1", []),
                    "high": data.get("quantile_0.9", []),
                }

            if forecast["median"]:
                logger.info(
                    f"🔮 Chronos forecast: {horizon} steps, "
                    f"median range [{min(forecast['median']):.2f}, {max(forecast['median']):.2f}]"
                )
                span.set_attribute("chronos.forecast_points", len(forecast["median"]))
                return forecast
            else:
                return None

        except requests.Timeout:
            logger.warning(f"⏱️  Chronos timeout after {self.timeout}s")
            span.set_attribute("error.timeout", True)
            return None

        except requests.ConnectionError:
            logger.warning("🔌 Chronos service unreachable (cc_chronos down?)")
            span.set_attribute("error.connection", True)
            return None

        except Exception as e:
            logger.error(f"Chronos adapter error: {e}")
            span.set_attribute("error", True)
            return None

    def health_check(self) -> bool:
        """
        Check if Chronos service is healthy.

        Returns:
            True if service responds to /health, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=1.0)
            return response.status_code == 200
        except Exception:
            return False
