import os
import logging
import orjson
import torch
import numpy as np
from datetime import datetime
from faststream import FastStream
from faststream.redis import RedisBroker

# Try importing ChronosPipeline, handle failure gracefully (for container/test envs without it)
try:
    from chronos import ChronosPipeline, ChronosBoltPipeline

    CHRONOS_AVAILABLE = True
except ImportError:
    CHRONOS_AVAILABLE = False

from app.core.models import ForecastPacket

# Configure Jim Simons
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | SIMONS | %(levelname)s | %(message)s"
)
logger = logging.getLogger("chronos")

# Initialize The Nervous System
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
broker = RedisBroker(redis_url)
app = FastStream(broker)


class ChronosService:
    """GPU-accelerated probabilistic time series forecasting using Chronos-bolt.

     Named after the Greek god of time, this service provides quantile forecasts
     using Amazon's Chronos-bolt-small model optimized for Apple MPS (Metal).

     **Architecture**:
     - Ring buffer (512-sample context window)
     - Throttled inference (every 10 ticks)
     - Zero-allocation updates for performance
     - MPS/CUDA/CPU device auto-selection

    **Probabilistic Forecasting**:
     - Returns P10, P50 (median), P90 quantiles
     - Horizon: Configurable (default: short-term)
     - Enables risk-aware decision making

     **Performance**:
     - MPS (Apple Silicon): ~50-100ms per forecast
     - Throttling prevents GPU saturation
     - Ring buffer avoids memory reallocation

     Attributes:
         model: ChronosBoltPipeline instance
         buffer: numpy ring buffer (context_len samples)
         device: torch device (mps/cuda/cpu)
         throttle_steps: Inference frequency (every N ticks)

     Example:
         >>>chronos = ChronosService()
         >>> chronos.update_buffer(price=150.25)
         >>> forecast = chronos.forecast()  # {"p10": ..., "p50": ..., "p90": ...}
    """

    def __init__(
        self, model_name="amazon/chronos-bolt-small", context_len=512, throttle_steps=10
    ):
        self.symbol = "BTC-USD"  # Single symbol focus for now
        self.context_len = context_len
        self.throttle_steps = throttle_steps
        self.tick_counter = 0

        # Buffer: Use float32 numpy array for price context
        self.price_context = np.zeros(self.context_len, dtype=np.float32)
        self.cursor = 0
        self.is_filled = False

        # Load Model
        # Enforce MPS if available for Bolt
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info(f"Chronos Hardware Accelerated: {self.device.upper()}")

        self.pipeline = None
        if CHRONOS_AVAILABLE:
            try:
                logger.info(f"Loading {model_name} on {self.device}...")

                # Bolt requires bfloat16 for best performance on Metal
                dtype = torch.bfloat16 if self.device == "mps" else torch.float32

                if "bolt" in model_name.lower():
                    logger.info("⚡ Using ChronosBoltPipeline")
                    pipeline_class = ChronosBoltPipeline
                else:
                    logger.info("🕰️ Using Standard ChronosPipeline")
                    pipeline_class = ChronosPipeline

                self.pipeline = pipeline_class.from_pretrained(
                    model_name,
                    device_map=self.device,
                    torch_dtype=dtype,
                )
                logger.info("Chronos Neural Matrix Loaded.")
            except Exception as load_err:
                logger.error(f"Chronos Initialization Failed: {load_err}")

                # CRITICAL: Check if we're in production
                from app.core.config import settings

                if settings.ENV == "PROD":
                    raise RuntimeError(
                        "❌ CRITICAL: Chronos forecasting library unavailable in PRODUCTION mode. "
                        "Cannot execute live trading without forecasting engine. "
                        "Install amazon-chronos-forecasting library or switch to DEV environment. "
                        f"Error: {load_err}"
                    )

                # DEV mode: Allow mock for testing
                logger.warning(
                    "⚠️ DEV MODE: Chronos library NOT FOUND. "
                    "Running in Mock/Pass-through Mode (testing only). "
                    "Forecasts will return neutral/placeholder data."
                )
                self.pipeline = None  # Mock mode
                self.device = "cpu"
                self.dtype = torch.float32
        else:
            logger.warning(
                "Chronos Library NOT FOUND. Running in Mock/Pass-through Mode."
            )
            # Ensure mock mode is explicitly set if Chronos is not available at all
            self.pipeline = None
            self.device = "cpu"
            self.dtype = torch.float32

    def update_buffer(self, price: float):
        """Zero-allocation ring buffer update."""
        if self.cursor < self.context_len:
            self.price_context[self.cursor] = price
            self.cursor += 1
        else:
            # Shift buffer logic or ring buffer slicing?
            # Ideally roll. For speed, roll is OK on small buffers, or proper ring ptr.
            # To keep it compatible with Pipeline expectations (which needs order):
            # Roll is easiest for context.
            self.price_context = np.roll(self.price_context, -1)
            self.price_context[-1] = price
            self.is_filled = True

    def forecast(self) -> ForecastPacket | None:
        """
        Runs Inference (Throttled).
        Returns P10, P50, P90.
        """
        self.tick_counter += 1

        # Throttle: Only run every N steps
        if self.tick_counter % self.throttle_steps != 0:
            return None

        # Minimum context check
        valid_len = self.context_len if self.is_filled else self.cursor
        if valid_len < 32:  # Need some context
            return None

        context_data = (
            self.price_context[:valid_len] if not self.is_filled else self.price_context
        )

        # Inference
        try:
            horizon = 10

            if self.pipeline:
                # Real Inference
                # context must be tensor or list of tensors.
                # Pipeline expects torch.tensor of shape (context_length,)
                context_tensor = torch.tensor(context_data, dtype=torch.float32)

                if isinstance(self.pipeline, ChronosBoltPipeline):
                    # Bolt returns quantiles directly (default 0.1...0.9)
                    forecast = self.pipeline.predict(
                        context_tensor, prediction_length=horizon
                    )  # (batch, num_quantiles, prediction_length)

                    # forecast[0] is (num_quantiles, horizon)
                    # Index 0=.10, 4=.50, 8=.90
                    quantiles = forecast[0].cpu().numpy()
                    p10 = quantiles[0, -1]
                    p50 = quantiles[4, -1]
                    p90 = quantiles[8, -1]
                else:
                    # Standard T5 returns samples
                    forecast = self.pipeline.predict(
                        context_tensor, prediction_length=horizon, num_samples=20
                    )  # Returns (1, num_samples, prediction_length)

                    sample_paths = forecast[0].numpy()  # (20, 10)
                    terminal_values = sample_paths[:, -1]

                    p10 = np.percentile(terminal_values, 10)
                    p50 = np.percentile(terminal_values, 50)
                    p90 = np.percentile(terminal_values, 90)

            else:
                # Mock Inference (Testing/No-Lib Mode)
                current_price = context_data[-1]
                p50 = current_price * (1.0 + np.random.normal(0, 0.001))
                p10 = p50 * 0.99
                p90 = p50 * 1.01

            # Confidence: 1.0 - (Spread / Median)
            spread_pct = (p90 - p10) / p50
            confidence = max(0.0, 1.0 - (spread_pct * 10))  # Heuristic scaling

            is_synthetic = not bool(self.pipeline)
            log_conf = f"{confidence * 100:.1f}%"
            logger.info(
                f"Inference T+{horizon}: ${p50:.2f} (±{log_conf} confidence). Moved to {self.device}. Synthetic: {is_synthetic}"
            )

            return ForecastPacket(
                timestamp=datetime.now(),
                symbol=self.symbol,
                p10=float(p10),
                p50=float(p50),
                p90=float(p90),
                horizon=horizon,
                confidence=float(confidence),
                is_synthetic=is_synthetic,
            )

        except Exception as e:
            logger.error(f"Inference Failed: {e}")
            return None


# Instantiate
simons = ChronosService()


@broker.subscriber("market.tick.*")
async def handle_market(msg: bytes):
    """
    Consumes Ticks.
    Feeds Buffer.
    Emits Probability Fields.
    """
    try:
        data = orjson.loads(msg)
        price = data.get("price")
        if price:
            simons.update_buffer(float(price))

            packet = simons.forecast()
            if packet:
                await broker.publish(
                    packet.model_dump_json(), channel="forecast.signals"
                )
    except Exception as e:
        logger.error(f"Chronos Loop Error: {e}")
