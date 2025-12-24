"""
Chronos-2 Time-Series Forecasting Adapter
Local inference using chronos-forecasting library (Hybrid Metal architecture).
"""

import logging
from typing import Dict, List, Optional

import numpy as np
import torch
from chronos import ChronosPipeline
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class ChronosAdapter:
    """Local Chronos-2 forecasting (amazon/chronos-t5-small) - zero-shot probabilistic predictions.

    **Architecture**: T5-based pretrained model (~46M params), PyTorch on CPU
    **Output**: Quantile forecasts (10th, 50th, 90th percentiles)
    **Performance**: ~1-3s inference on M1/M2/M3, min 10 observations required
    """

    def __init__(self, model_name: str = "amazon/chronos-t5-small"):
        """
        Initialize Chronos adapter with local model.

        Args:
            model_name: HuggingFace model identifier (defaults to chronos-t5-small)
        """
        self.model_name = model_name
        self.device = self._get_device()
        self.pipeline = None

        # Lazy loading - only load model on first predict() call
        logger.info(
            f"ChronosAdapter initialized (model: {model_name}, device: {self.device})"
        )

    def _get_device(self) -> str:
        """Determine best available device"""
        # Force CPU for Chronos to avoid MPS Meta Tensor bug
        return "cpu"

    def _ensure_loaded(self):
        """Lazy load the Chronos pipeline on first use"""
        if self.pipeline is None:
            logger.info(f"🔮 Loading Chronos model: {self.model_name}...")
            try:
                self.pipeline = ChronosPipeline.from_pretrained(
                    self.model_name,
                    # device_map removed to force standard PyTorch load (avoids accelerate/meta bug)
                    torch_dtype=torch.float32,
                )
                self.pipeline.model.to(self.device)
                logger.info(f"✅ Chronos model loaded on {self.device}")
            except Exception as e:
                logger.error(f"❌ Failed to load Chronos: {e}")
                raise

    @tracer.start_as_current_span("chronos_predict")
    def predict(
        self, prices: List[float], horizon: int = 10, num_samples: int = 20
    ) -> Optional[Dict[str, List[float]]]:
        """
        Generate probabilistic forecast using Chronos-2.

        Args:
            prices: Historical price context (last N observations)
            horizon: Number of steps to forecast ahead
            num_samples: Number of Monte Carlo samples for quantile estimation

        Returns:
            Dict with keys:
                - median: List[float] (50th percentile forecast)
                - low: List[float] (10th percentile - bearish scenario)
                - high: List[float] (90th percentile - bullish scenario)
            Returns None if errors occur.
        """
        span = trace.get_current_span()
        span.set_attribute("chronos.context_length", len(prices))
        span.set_attribute("chronos.horizon", horizon)
        span.set_attribute("chronos.device", self.device)

        if len(prices) < 10:
            logger.warning("Chronos: Insufficient context (need ≥10 points)")
            return None

        try:
            # Ensure model is loaded
            self._ensure_loaded()

            # Convert to tensor
            input_tensor = torch.tensor(prices, dtype=torch.float32)

            # Generate forecast samples
            forecast_samples = self.pipeline.predict(
                inputs=input_tensor,
                prediction_length=horizon,
                num_samples=num_samples,
            )

            # Convert to numpy and calculate quantiles
            # Shape is (batch=1, num_samples, horizon) - squeeze batch dim
            samples_raw = forecast_samples.numpy()
            samples = samples_raw.squeeze(0)  # Now (num_samples, horizon)

            # Calculate quantiles across samples (axis=0)
            median = np.quantile(samples, 0.5, axis=0).tolist()
            low = np.quantile(samples, 0.1, axis=0).tolist()
            high = np.quantile(samples, 0.9, axis=0).tolist()

            forecast = {
                "median": median,
                "low": low,
                "high": high,
            }

            logger.info(
                f"🔮 Chronos forecast: {horizon} steps, "
                f"median range [{min(median):.2f}, {max(median):.2f}]"
            )
            span.set_attribute("chronos.forecast_points", len(median))
            return forecast

        except Exception as e:
            import traceback

            logger.error(f"Chronos inference error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            span.set_attribute("error", True)
            return None

    def health_check(self) -> bool:
        """
        Check if Chronos model can be loaded.

        Returns:
            True if model loads successfully, False otherwise
        """
        try:
            self._ensure_loaded()
            return self.pipeline is not None
        except Exception:
            return False
