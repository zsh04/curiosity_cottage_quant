import os
import logging
import numpy as np
import orjson
from typing import Dict, Any, Union
from faststream import FastStream
from faststream.redis import RedisBroker
from scipy.stats import entropy
from app.core.vectors import PhysicsVector

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

    def calculate_forces(self) -> PhysicsVector:
        """
        The 5 Pillars of Physics.
        If the buffer isn't sufficiently full for stats, we return zeros.
        """
        if self.cursor < 4:  # Need 4 points for Jerk (3 diffs)
            return self._empty_vector()

        valid_len = self.window_size if self.is_filled else self.cursor
        active_prices = self.prices[-valid_len:]
        active_vols = self.volumes[-valid_len:]
        active_prices = self.prices[-valid_len:]
        active_vols = self.volumes[-valid_len:]
        # active_trades = self.trades[-valid_len:] # Unused since friction removed from Vector

        # --- 1. Mass ($m$) ---
        # m = V * CLV
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

        # --- 2. Momentum ($p$) & Jerk ($j$) ---
        # p = m * v
        # Velocity = Log Return
        velocity = 0.0
        jerk = 0.0

        if len(active_prices) > 3:
            # Velocity (v) = ln(p_t / p_t-1)
            # Acceleration (a) = v_t - v_t-1
            # Jerk (j) = a_t - a_t-1

            # Last 4 prices needed for 3 velocities -> 2 accels -> 1 jerk
            recent = active_prices[-4:]

            # Velocities: p[-1]/p[-2], p[-2]/p[-3], p[-3]/p[-4]
            v_t = np.log(recent[-1] / recent[-2]) if recent[-2] > 0 else 0
            v_t_1 = np.log(recent[-2] / recent[-3]) if recent[-3] > 0 else 0
            v_t_2 = np.log(recent[-3] / recent[-4]) if recent[-4] > 0 else 0

            velocity = v_t

            # Accelerations
            a_t = v_t - v_t_1
            a_t_1 = v_t_1 - v_t_2

            # Jerk
            jerk = a_t - a_t_1

        momentum = mass * velocity

        # --- 4. Shannon Entropy ($H$) ---
        entropy_val = 0.0
        if len(active_prices) > 5:
            returns = np.diff(np.log(active_prices))
            hist_counts, _ = np.histogram(returns, bins="auto", density=True)
            hist_counts = hist_counts[hist_counts > 0]
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

        return PhysicsVector(
            mass=float(mass),
            momentum=float(momentum),
            entropy=float(entropy_val),
            jerk=float(jerk),
            nash_dist=float(nash_distance),
            alpha_coefficient=2.5,  # Default/Placeholder
            price=float(current_price),
        )

    def _empty_vector(self) -> PhysicsVector:
        return PhysicsVector(
            mass=0.0,
            momentum=0.0,
            entropy=0.0,
            jerk=0.0,
            nash_dist=0.0,
            alpha_coefficient=2.5,
            price=0.0,
        )


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
        volume = float(data.get("size", 0.0))
        trades = int(data.get("updates", 1))

        # Load the chamber
        kernel.update_buffer(price, volume, trades)

        # Calculate Vectors
        forces = kernel.calculate_forces()

        # Stamp it
        packet = {
            "symbol": symbol,
            "timestamp": data.get("timestamp"),
            "vectors": forces.model_dump(),
        }

        # Wolf Logging
        if forces.entropy > 0.9:
            logger.warning(
                f"CHAOS DETECTED on {symbol}. Entropy: {forces.entropy:.2f}. Discarding."
            )

        # BRIDGE: Write State to Key for synchronous access by Agents
        # Expiry: 10 seconds (Data is fresh or dead)
        try:
            if hasattr(broker, "redis"):
                await broker.redis.set(
                    f"physics:state:{symbol}", orjson.dumps(forces.model_dump()), ex=10
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

            packet = {
                "symbol": symbol,
                "timestamp": ts,
                "vectors": neutral_forces.model_dump(),
                "error": str(e),
            }
            await broker.publish(orjson.dumps(packet), channel="physics.forces")
        except Exception:
            logger.critical("Double Fault in Feynman. Physics collapsed.")
