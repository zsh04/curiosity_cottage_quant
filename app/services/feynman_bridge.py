import os
import redis
import orjson
import logging
from typing import Dict, Any, List

logger = logging.getLogger("feynman_bridge")


class FeynmanBridge:
    """Redis-backed physics state accessor - reads live kinematics from FeynmanService.

    Acts as a synchronous bridge between Boyd Agent and the async FeynmanService kernel.
    Reads precomputed physics vectors from Redis (written by FeynmanService) to avoid
    recomputation and ensure consistency.

    **Architecture**:
    - Reads from `physics:state:{symbol}` Redis keys
    - Falls back to zero-gravity defaults if unavailable
    - Provides legacy adapters for stateless kinematics

    **Physics Vector (5-Pillar)**:
    1. mass: Price inertia
    2. momentum: Velocity * mass
    3. friction: Drag coefficient
    4. entropy: Shannon entropy of returns
    5. nash_dist: Nash distance from mode
    6. regime: Market regime (Gaussian/Lévy/Critical)
    7. alpha_coefficient: Power law exponent

    Attributes:
        redis: Sync Redis client for blocking access
        price_history_buffer: Internal buffer for legacy methods

    Example:
        >>> bridge = FeynmanBridge()
        >>> forces = bridge.get_forces("SPY")
        >>> print(forces["momentum"], forces["regime"])
    """

    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        # Sync Redis Client for blocking Agent access
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        # Internal buffer for simple history if needed
        self.price_history_buffer = []
        self.is_initialized = True

    def get_forces(self, symbol: str) -> Dict[str, float]:
        """
        Fetches the latest 5-Pillar Physics Vector for a symbol.
        """
        try:
            data = self.redis.get(f"physics:state:{symbol}")
            if data:
                return orjson.loads(data)
        except Exception as e:
            logger.debug(f"Feynman Bridge Miss ({symbol}): {e}")

        # Fallback / Zero Gravity
        return {
            "mass": 0.0,
            "momentum": 0.0,
            "friction": 0.0,
            "entropy": 0.0,
            "nash_dist": 0.0,
            "regime": "WAIT",
            "alpha_coefficient": 2.5,
        }

    def calculate_kinematics(
        self, prices: List[float] = None, new_price: float = None
    ) -> Dict[str, float]:
        """
        Legacy adapter for Boyd Agent.
        If a symbol context existed, we would query get_forces.
        Since this method is stateless (passing prices/new_price), we implement basic fallback kinematics
        or return data from Redis if we could infer symbol (which we can't here easily without state).
        """
        import numpy as np

        # If we have new_price, append it (simulating update)
        target_prices = []
        if prices:
            target_prices = list(prices)
        if new_price:
            target_prices.append(new_price)

        if not target_prices or len(target_prices) < 2:
            return {"velocity": 0.0, "acceleration": 0.0}

        # Simple Log Return Velocity (p - p_1)
        # This is a fallback. The Real Velocity is in get_forces()['momentum'] / mass (if we had symbol)
        try:
            v = np.log(target_prices[-1] / target_prices[-2])
            # Acceleration
            v_prev = 0.0
            if len(target_prices) > 2:
                v_prev = np.log(target_prices[-2] / target_prices[-3])
            a = v - v_prev

            return {"velocity": float(v), "acceleration": float(a)}
        except Exception:
            return {"velocity": 0.0, "acceleration": 0.0}

    def analyze_regime(self, buffer: List[float]) -> Dict[str, Any]:
        # Stub to satisfy Agent calls - ideally should read "regime" from get_forces
        return {"regime": "Gaussian", "alpha": 2.5}

    def calculate_hurst_and_mode(self, prices: List[float]) -> Dict[str, Any]:
        return {"hurst": 0.5, "strategy_mode": "Neutral"}

    def calculate_qho_levels(self, prices: List[float]) -> Dict[str, Any]:
        return {"energy_state": 0.0}
