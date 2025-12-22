import os
import redis
import orjson
import logging
from typing import Dict, Any, List

logger = logging.getLogger("feynman_bridge")


class FeynmanBridge:
    """
    The Feynman Bridge.
    Reads live physics state directly from the Redis Keys written by FeynmanService (The Kernel).
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
        except:
            return {"velocity": 0.0, "acceleration": 0.0}

    def analyze_regime(self, buffer: List[float]) -> Dict[str, Any]:
        # Stub to satisfy Agent calls - ideally should read "regime" from get_forces
        return {"regime": "Gaussian", "alpha": 2.5}

    def calculate_hurst_and_mode(self, prices: List[float]) -> Dict[str, Any]:
        return {"hurst": 0.5, "strategy_mode": "Neutral"}

    def calculate_qho_levels(self, prices: List[float]) -> Dict[str, Any]:
        return {"energy_state": 0.0}
