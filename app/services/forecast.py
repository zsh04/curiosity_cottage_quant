"""
The Unified Forecasting Engine (Oracle).

Merges Recursive Neural Networks (Chronos-Bolt) with Retrieval Augmented Forecasting (RAF)
to generate high-confidence, physics-constrained market predictions.

Identity: The Chief Architect
"""

import asyncio
import logging
import torch
import numpy as np
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from app.core.config import settings
from app.services.rag_forecast import MarketMemory

# Try importing ChronosPipeline
try:
    from chronos import ChronosPipeline, ChronosBoltPipeline

    CHRONOS_AVAILABLE = True
except ImportError:
    CHRONOS_AVAILABLE = False

# Logger
logger = logging.getLogger("Forecaster")
logging.basicConfig(level=logging.INFO)


class TimeSeriesForecaster:
    """
    Unified Forecasting & Memory System.
    """

    def __init__(self):
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.dtype = torch.bfloat16 if self.device == "mps" else torch.float32

        # 1. Load Chronos-Bolt
        self.pipeline = None
        self._load_chronos()

        # 2. Warmup Graph
        self._warmup()

        # 3. Initialize MarketMemory (LanceDB)
        logger.info("🧠 Initializing Market Memory (LanceDB)...")
        self.memory = MarketMemory()

        # Thread Pool for blocking Inference
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _load_chronos(self):
        """Load Chronos-Bolt model implementation."""
        if not CHRONOS_AVAILABLE:
            logger.warning("⚠️ Chronos not available. Running in PLACEHOLDER mode.")
            return

        model_name = "amazon/chronos-bolt-small"
        logger.info(f"🔮 Loading {model_name} on {self.device.upper()}...")

        try:
            self.pipeline = ChronosBoltPipeline.from_pretrained(
                model_name,
                device_map=self.device,
                torch_dtype=self.dtype,
            )
            logger.info("✅ Chronos Neural Matrix Loaded.")
        except Exception as e:
            logger.error(f"❌ Failed to load Chronos: {e}")

    def _warmup(self):
        """Run a dummy inference to compile the graph (MPS)."""
        if not self.pipeline:
            return

        logger.info("🔥 Warming up inference graph...")
        try:
            dummy = torch.randn(1, 64, device=self.device, dtype=self.dtype)
            self.pipeline.predict(dummy, prediction_length=settings.FORECAST_HORIZON)
            logger.info("✅ Warmup Complete.")
        except Exception as e:
            logger.warning(f"⚠️ Warmup failed: {e}")

    async def predict_ensemble(
        self,
        context_tensor: torch.Tensor,
        current_prices: List[float],
        cutoff_timestamp: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        The Master Method: Async + Batch + RAF + Fusion.

        Args:
            context_tensor: Torch tensor of historical prices (Shape: Batch x Time) or (Time,).
            current_prices: Raw list of recent prices (used for RAF normalization).
            cutoff_timestamp: Optional datetime to enforce causality in RAF.

        Returns:
            Dict with 'signal', 'confidence', 'chronos', 'raf', 'meta'.
        """
        if context_tensor.ndim == 1:
            context_tensor = context_tensor.unsqueeze(0)

        # STEP A: Chronos (Async Thread)
        chronos_future = asyncio.get_running_loop().run_in_executor(
            self.executor, self._run_chronos_batch, context_tensor
        )

        # STEP B: RAF (Vector Search)
        # Normalize for RAG: (Window - Mean) / Std
        # Use last RAF_WINDOW_SIZE prices
        window_size = settings.RAF_WINDOW_SIZE
        if len(current_prices) >= window_size:
            recent_window = np.array(current_prices[-window_size:], dtype=np.float32)
            mean = np.mean(recent_window)
            std = np.std(recent_window)

            if std > 0:
                normalized_vector = ((recent_window - mean) / std).tolist()
                raf_result = self.memory.search_analogs(
                    normalized_vector, cutoff_timestamp=cutoff_timestamp
                )
            else:
                raf_result = {"weighted_outcome": 0.0, "confidence": 0.0, "matches": []}
        else:
            raf_result = {"weighted_outcome": 0.0, "confidence": 0.0, "matches": []}

        # Await Chronos
        chronos_result = await chronos_future

        # Step C: Relativity (Timeframe Harmony)
        # Assuming context_tensor is 1m data (Horizon 12m)
        # We need a proxy for the higher timeframe (5m).
        # For efficiency, we won't run a second inference pass yet (latency).
        # We will infer the HTF Trend from the LTF Context Window.
        # "Zoom Out" = aggregate last 60 points of 1m data -> 12 points of 5m data?
        # Or simply check if the 1m context trend aligns with the 1m forecast.

        # RELATIVITY OPERATOR Logic:
        # 1. Calculate historical trend of the context window (Past Velocity)
        # 2. Compare with Forecast Trend (Future Velocity)
        # 3. If Past was Up and Future is Up -> Concordance
        # 4. If Past was Down and Future is Up -> Reversion (Lower Confidence)

        # NOTE: A true HTF check needs 5m bars. For now, we use "Past vs Future" as the relativity check
        # until we wire up multi-timeframe inputs in Phase 33.

        context_prices = context_tensor.cpu().numpy().flatten()
        if len(context_prices) > 10:
            start_p = context_prices[0]
            end_p = context_prices[-1]
            past_trend = (end_p - start_p) / start_p if start_p != 0 else 0.0
        else:
            past_trend = 0.0

        chronos_result["past_trend"] = float(past_trend)

        # STEP D: Fusion & Guardrails
        return self._fuse_signals(chronos_result, raf_result)

    def _run_chronos_batch(self, tensor: torch.Tensor) -> Dict[str, float]:
        """
        Blocking inference call.
        """
        if not self.pipeline:
            return {"p10": 0.0, "p50": 0.0, "p90": 0.0, "trend": 0.0}

        try:
            # Ensure tensor is on device
            if tensor.device.type != self.device:
                tensor = tensor.to(self.device, dtype=self.dtype)

            forecast = self.pipeline.predict(
                tensor, prediction_length=settings.FORECAST_HORIZON
            )
            # Bolt: (batch, num_quantiles, horizon)
            # We take the first batch item for now (Single Stream focus)
            quantiles = forecast[0].float().cpu().numpy()  # Transfer back

            # Extract Terminal Values (End of Horizon)
            p10 = quantiles[0, -1]  # 0.1 quantile
            p50 = quantiles[4, -1]  # 0.5 quantile
            p90 = quantiles[8, -1]  # 0.9 quantile

            # Trend: (P50_Final - P50_Initial) / P50_Initial?
            # Or just expected move.
            # Usually we compare to current price (last in context).
            # But context is normalized? No, input to Chronos is raw prices usually.
            # Assuming tensor contains raw prices.
            last_price = float(tensor[0, -1].item())

            trend_pct = (p50 - last_price) / last_price if last_price != 0 else 0.0

            return {
                "p10": float(p10),
                "p50": float(p50),
                "p90": float(p90),
                "trend": float(trend_pct),
                "spread": float((p90 - p10) / p50),
            }

        except Exception as e:
            logger.error(f"Chronos Inference Error: {e}")
            return {"p10": 0.0, "p50": 0.0, "p90": 0.0, "trend": 0.0}

    def _fuse_signals(
        self, chronos: Dict[str, float], raf: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combine Neural (Chronos) and Memory (RAF) signals.

        Logic:
        1. If both agree on Direction -> Boost Confidence.
        2. If RAF confidence is high (>0.8) and contradicts Chronos -> Veto/Dampen.
        3. If Chronos Spread is wide (High Uncertainty) -> Rely on RAF.
        """
        chronos_trend = chronos.get("trend", 0.0)
        raf_trend = raf.get("weighted_outcome", 0.0)
        raf_conf = raf.get("confidence", 0.0)

        # Directions
        c_dir = np.sign(chronos_trend)
        r_dir = np.sign(raf_trend)

        # Base signal is Chronos (The Oracle)
        final_conviction = abs(chronos_trend)
        signal_type = "NEUTRAL"

        # Agreement Check
        agreement = c_dir == r_dir

        if agreement:
            # Resonance!
            confidence = 0.8 + (raf_conf * 0.2)  # Boost
            reasoning = f"Resonance: Neural ({chronos_trend:.2%}) and Memory ({raf_trend:.2%}) align."
        else:
            # Conflict
            if raf_conf > 0.85:  # Strong Memory Match
                # Memory Veto
                confidence = 0.2
                reasoning = f"Conflict: Strong Memory Analog ({raf_trend:.2%}) opposes Neural ({chronos_trend:.2%}). Caution."
                c_dir = 0  # Neutralize
            else:
                # Trust Neural, ignore weak memory
                confidence = 0.6
                reasoning = f"Divergence: Neural ({chronos_trend:.2%}) overrides weak Memory ({raf_trend:.2%})."

                confidence = 0.6
                reasoning = f"Divergence: Neural ({chronos_trend:.2%}) overrides weak Memory ({raf_trend:.2%})."

        # RELATIVITY PENALTY (Timeframe / Trend Alignment)
        past_trend = chronos.get("past_trend", 0.0)
        # If fighting the trend (Reversion), reduce confidence
        # Unless relying on Mean Reversion Strategy explicitly?
        # For "The Oracle" (Trend Follower), we punish fighting the immediate past trend.
        if np.sign(chronos_trend) != np.sign(past_trend) and abs(past_trend) > 0.001:
            confidence *= 0.8  # 20% Penalty for counter-trend
            reasoning += f" [Relativity: Fighting Trend ({past_trend:.2%})]"

        # Determine Signal
        if c_dir > 0:
            signal_type = "BUY"
        elif c_dir < 0:
            signal_type = "SELL"

        return {
            "signal": signal_type,
            "confidence": float(confidence),
            "reasoning": reasoning,
            "components": {"chronos": chronos, "raf": raf},
        }
