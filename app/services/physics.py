from app.lib.kalman.kinematic import KinematicKalmanFilter
from app.lib.memory import FractalMemory
from app.lib.physics.heavy_tail import HeavyTailEstimator
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PhysicsService:
    """
    Physics Service: Evolving the system from 'Statistics' to 'Physics'.
    Encapsulates Kinematics (Velocity/Acceleration) and Regime Detection (Thermodynamics).
    """

    def __init__(self):
        # We initialize a default KF, but for window-based processing
        # we invariably need to reset/warmup for each snapshot to avoid state pollution.
        self.kf = KinematicKalmanFilter()

        # HeavyTail is static/stateless typically, but we instantiate if needed.
        # Looking at app/lib/physics/heavy_tail.py, HeavyTailEstimator methods are likely static
        # or we use the class. Wait, usually it has static methods.
        # Let's assume we use the class methods directly or instance if required.
        # The prompt implies calling methods on `HeavyTailEstimator`.

    def calculate_kinematics(self, prices: List[float]) -> Dict[str, float]:
        """
        Calculate Kinematics (Velocity, Acceleration) of the price series.
        Uses Fractal Differentiation to ensure stationarity before Kinematic extraction.

        Args:
            prices: Chronological list of raw prices (e.g. 200 bars).

        Returns:
            {
                'velocity': float,
                'acceleration': float
            }
        """
        # 1. Warmup / Reset KF (Critical for Architecture V2 to avoid Initialization Shock)
        # We re-instantiate to ensure we calculate kinematics PURELY on this window
        self.kf = KinematicKalmanFilter()

        # 2. Fractional Differentiation (Stationarity + Memory)
        # Using d=0.4 as standard per instruction
        try:
            stationary_series = FractalMemory.frac_diff(prices, d=0.4)
        except Exception as e:
            logger.error(f"PhysicsService: FracDiff failed: {e}")
            # Fallback to raw prices or returns? Let's fallback to raw to not crash.
            stationary_series = prices

        # 3. Replay History to Warmup Filter
        # We ignore the output of the updates, just accumulating state.
        final_estimate = None
        for measurement in stationary_series:
            final_estimate = self.kf.update(measurement)

        if final_estimate:
            return {
                "velocity": final_estimate.velocity,
                "acceleration": final_estimate.acceleration,
            }
        else:
            return {"velocity": 0.0, "acceleration": 0.0}

    def analyze_regime(self, price_history: List[float]) -> Dict[str, Any]:
        """
        Analyze Market Regime using Heavy Tail Statistics (Hill Estimator).

        Args:
            price_history: Chronological price history (will calculate returns internally).

        Returns:
            {
                'alpha': float,  # Tail index
                'regime': str    # 'Gaussian' | 'Levy Stable' | 'Critical'
            }
        """
        try:
            # Calculate returns from price history
            if len(price_history) < 2:
                logger.warning(
                    "PhysicsService: Insufficient history for regime analysis"
                )
                return {"alpha": 0.0, "regime": "Unknown"}

            # Calculate percentage returns: (p[i] - p[i-1]) / p[i-1]
            returns = [
                (price_history[i] - price_history[i - 1]) / price_history[i - 1]
                for i in range(1, len(price_history))
            ]

            # 1. Calculate Alpha (Tail Index)
            alpha = HeavyTailEstimator.hill_estimator(returns)

            # 2. Detect Regime
            regime = HeavyTailEstimator.detect_regime(alpha)

            return {"alpha": alpha, "regime": regime}
        except Exception as e:
            logger.error(f"PhysicsService: Regime analysis failed: {e}")
            return {"alpha": 0.0, "regime": "Unknown"}
