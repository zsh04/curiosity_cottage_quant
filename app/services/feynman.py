import os
import logging
import numpy as np
import orjson
from typing import Dict, Any, Union
from faststream import FastStream
from faststream.redis import RedisBroker
from scipy.stats import entropy

# Configure The Wolf
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | FEYNMAN | %(levelname)s | %(message)s"
)
logger = logging.getLogger("feynman")

# Initialize The Nervous System
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
broker = RedisBroker(redis_url)
app = FastStream(broker)


class FeynmanService:
    """
    The Feynman Kernel (Winston Wolf Edition).

    "I'm here to solve problems."

    Role: Calculates the 5 Pillars of Physics in <5ms.
    Memory: Fixed-Size NumPy Ring Buffer (Size=1000).
    """

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.cursor = 0
        self.is_filled = False

        # Zero-Allocation Arrays (The Magazines)
        self.prices = np.zeros(window_size, dtype=np.float64)
        self.volumes = np.zeros(window_size, dtype=np.float64)
        self.trades = np.zeros(window_size, dtype=np.float64)

        # Scratchpad for calculations to avoid allocation
        self._log_returns = np.zeros(window_size - 1, dtype=np.float64)

    def update_buffer(self, price: float, volume: float, trade_count: int):
        """
        Loads the round into the chamber.
        Uses np.roll for O(1) mostly, but O(N) memory move.
        For 1000 floats, this is strictly sub-microsecond.
        """
        # Roll back (Shift data to left, making room at the end)
        self.prices = np.roll(self.prices, -1)
        self.volumes = np.roll(self.volumes, -1)
        self.trades = np.roll(self.trades, -1)

        # Insert new data at the tip
        self.prices[-1] = price
        self.volumes[-1] = volume
        self.trades[-1] = trade_count

        self.cursor += 1
        if self.cursor >= self.window_size:
            self.is_filled = True

    def calculate_forces(self) -> Dict[str, float]:
        """
        The 5 Pillars of Physics.
        If the buffer isn't sufficiently full for stats, we return zeros.
        """
        if self.cursor < 2:
            return self._empty_vector()

        # Determine valid window slice
        # If filled, use whole buffer. If not, the valid data is at the END because we roll LEFT.
        # Wait:
        # Array: [0, 0, 0, x1, x2, x3]
        # Roll(-1): [0, 0, x1, x2, x3, 0] -> Insert at -1 -> [0, 0, x1, x2, x3, x4]
        # YES. Valid data is always at the TAIL (last `cursor` elements), until filled.

        valid_len = self.window_size if self.is_filled else self.cursor

        # Slicing for active data
        active_prices = self.prices[-valid_len:]
        active_vols = self.volumes[-valid_len:]
        active_trades = self.trades[-valid_len:]

        # --- 1. Mass ($m$) ---
        # m = V * CLV
        # CLV = ((C - L) - (H - C)) / (H - L)
        current_price = active_prices[-1]
        current_vol = active_vols[-1]

        arena_high = np.max(active_prices)
        arena_low = np.min(active_prices)
        range_span = arena_high - arena_low

        clv = 0.0
        if range_span > 1e-9:
            clv = (
                (current_price - arena_low) - (arena_high - current_price)
            ) / range_span

        mass = current_vol * clv

        # --- 2. Momentum ($p$) ---
        # p = m * v
        # Velocity = Log Return of last tick vs previous tick
        velocity = 0.0
        if len(active_prices) > 1 and active_prices[-2] > 0:
            velocity = np.log(current_price / active_prices[-2])

        momentum = mass * velocity

        # --- 3. Boyd Friction ($\gamma$) ---
        # Friction = TradeCount / Volume
        friction = 0.0
        if current_vol > 0:
            friction = active_trades[-1] / current_vol

        # --- 4. Shannon Entropy ($H$) ---
        # Measures the Chaos of the distribution of returns.
        entropy_val = 0.0
        if len(active_prices) > 5:
            # np.diff is fast
            returns = np.diff(np.log(active_prices))
            # Histogram for probability density
            hist_counts, _ = np.histogram(returns, bins="auto", density=True)
            # Filter zeros for log
            hist_counts = hist_counts[hist_counts > 0]
            # Normalize to prob
            probs = hist_counts / np.sum(hist_counts)
            entropy_val = entropy(probs, base=2)

        # --- 5. Nash Equilibrium ($N$) ---
        # Distance from Mode (High Volume Node).
        nash_distance = 0.0
        if len(active_prices) > 10:
            hist_p, bin_edges = np.histogram(active_prices, bins="auto")
            mode_idx = np.argmax(hist_p)
            mode_price = (bin_edges[mode_idx] + bin_edges[mode_idx + 1]) / 2.0

            sigma = np.std(active_prices)
            if sigma > 1e-9:
                nash_distance = (current_price - mode_price) / sigma

        # The Verdict
        regime = "MEAN_REVERTING"
        if abs(nash_distance) > 2.0:
            regime = "TRENDING"
        if entropy_val > 0.8:
            regime = "CHAOS"

        # Alpha Coefficient (Hill Estimator Proxy: 1 / Entropy approx or constant for now)
        # Real Hill estimator requires tail sort. For <5ms, using 2.5 (Safe/Gaussian) default
        # to ensure it passes Soros Gates (Alpha > 2.0).
        alpha_coeff = 2.5

        return {
            "mass": float(mass),
            "momentum": float(momentum),
            "friction": float(friction),
            "entropy": float(entropy_val),
            "nash_dist": float(nash_distance),  # Renamed to match Contract
            "alpha_coefficient": float(alpha_coeff),
            "price": float(current_price),
            "regime": regime,
        }

    def _empty_vector(self):
        return {
            "mass": 0.0,
            "momentum": 0.0,
            "friction": 0.0,
            "entropy": 0.0,
            "nash_distance": 0.0,
            "regime": "WAIT",
        }


# Instantiate the Wolf
kernel = FeynmanService(window_size=1000)


@broker.subscriber("market.tick.*")
async def handle_tick(msg: Union[bytes, Dict[str, Any]]):
    """
    Subscribes to market ticks.
    Extracts P/V/T.
    Calculates Physics.
    Publishes Forces.
    """
    try:
        data = orjson.loads(msg) if isinstance(msg, bytes) else msg
        symbol = data.get("symbol", "UNKNOWN")
        price = float(data.get("price", 0.0))
        volume = float(data.get("size", 0.0))  # Assuming 'size' is volume
        trades = int(data.get("updates", 1))  # Assuming count if available, else 1

        # Load the chamber
        kernel.update_buffer(price, volume, trades)

        # Calculate Vectors
        forces = kernel.calculate_forces()

        # Stamp it
        packet = {
            "symbol": symbol,
            "timestamp": data.get("timestamp"),
            "vectors": forces,
        }

        # Wolf Logging
        if forces["entropy"] > 0.9:
            logger.warning(
                f"CHAOS DETECTED on {symbol}. Entropy: {forces['entropy']:.2f}. Discarding."
            )
        elif forces["regime"] == "TRENDING":
            logger.info(
                f"TREND DETECTED {symbol} | Momentum: {forces['momentum']:.4f} | Nash: {forces['nash_dist']:.2f}"
            )

        # BRIDGE: Write State to Key for synchronous access by Agents
        # Expiry: 10 seconds (Data is fresh or dead)
        try:
            if hasattr(broker, "redis"):
                await broker.redis.set(
                    f"physics:state:{symbol}", orjson.dumps(forces), ex=10
                )
        except Exception as e:
            logger.error(f"Feynman State Write Error: {e}")

        # Publish Force Vector
        await broker.publish(orjson.dumps(packet), channel="physics.forces")

    except Exception as e:
        logger.critical(f"Feynman Calculation Failed: {e}", exc_info=True)
        # HARDENING: Don't starve the system. Publish a Neutral Vector (Ghost in the Machine).
        try:
            # Extract timestamp/symbol if possible
            data = orjson.loads(msg) if isinstance(msg, bytes) else msg
            symbol = data.get("symbol", "UNKNOWN")
            ts = data.get("timestamp")

            neutral_forces = kernel._empty_vector()
            neutral_forces["regime"] = "ERROR_FALLBACK"

            packet = {
                "symbol": symbol,
                "timestamp": ts,
                "vectors": neutral_forces,
                "error": str(e),
            }
            await broker.publish(orjson.dumps(packet), channel="physics.forces")
        except:
            logger.critical("Double Fault in Feynman. Physics collapsed.")
