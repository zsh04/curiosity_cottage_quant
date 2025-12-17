from app.lib.kalman.kinematic import KinematicKalmanFilter
from app.lib.memory import FractalMemory
from app.lib.physics.heavy_tail import HeavyTailEstimator
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from opentelemetry import trace
from app.core import metrics as business_metrics
from scipy.integrate import quad

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class PhysicsService:
    """
    Physics Service: Real-time kinematic tracking and regime detection.

    CRITICAL DESIGN DECISION (Real Money Trading):
    - Kalman Filter is STATEFUL for continuous price tracking
    - First call does warmup on historical data
    - Subsequent calls update with single new price
    - Maintains covariance matrix convergence

    This is the CORRECT implementation for live trading.
    """

    def __init__(self):
        """
        Initialize stateful Kalman Filter.
        Filter maintains state across calls for continuous tracking.
        """
        self.kf = KinematicKalmanFilter()
        self.is_initialized = False
        self.last_price = None

        # For regime detection, we maintain a rolling window
        self.price_history_buffer: List[float] = []
        self.max_history_size = 200  # Keep last 200 bars for regime

    def calculate_tunneling_probability(
        self, price: float, resistance: float, volatility: float
    ) -> float:
        """
        Calculate probability of price tunneling through a resistance level
        using WKB approximation (Quantum Mechanics).
        """
        if volatility <= 0:
            return 0.0

        # Quantum Parameters (Normalized)
        m = 1.0  # Mass
        hbar = 1.0  # Planck constant

        # Energy (Kinetic)
        # E = 0.5 * m * v^2
        E = 0.5 * m * (volatility**2)

        # Potential Barrier
        V = resistance

        # Classical Breakout
        if E > V:
            return 1.0

        # Quantum Tunneling (E < V)
        # Barrier width (d) modeled as distance to resistance
        barrier_width = max(0.0, resistance - price)

        # Integrand: sqrt(2*m*(V-E))
        # For rectangular barrier, this is constant.
        def integrand(x):
            return np.sqrt(2 * m * (V - E))

        try:
            # Integrate over barrier width
            integral, _ = quad(integrand, 0, barrier_width)

            # WKB Probability: T = exp(-2 * integral / hbar)
            # Since hbar=1, we ignore division
            prob = np.exp(-2 * integral)
            return float(prob)
        except Exception as e:
            logger.error(f"WKB Integration failed: {e}")
            return 0.0

    @tracer.start_as_current_span("physics_calculate_kinematics")
    def calculate_kinematics(
        self, prices: Optional[List[float]] = None, new_price: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate Kinematics + Quantitative Tunneling Probability.
        """
        # Maintain history buffer for resistance/volatility calc
        if prices:
            self.price_history_buffer = list(prices)[-self.max_history_size :]
        elif new_price:
            self.price_history_buffer.append(new_price)
            if len(self.price_history_buffer) > self.max_history_size:
                self.price_history_buffer.pop(0)

        # Calculate Inputs for WKB
        current_price = new_price if new_price else (prices[-1] if prices else 0)

        if len(self.price_history_buffer) > 20:
            # Resistance = Rolling Max (Simple local resistance)
            resistance = max(self.price_history_buffer)

            # Volatility = Std Dev of price (Absolute volatility)
            volatility = np.std(self.price_history_buffer[-20:])

            # WKB Calculation
            tunneling_prob = self.calculate_tunneling_probability(
                current_price, resistance, volatility
            )
        else:
            tunneling_prob = 0.0

        # ... (Existing Kalman Logic) ...
        # MODE 1: Warmup
        if prices is not None and not self.is_initialized:
            kf_result = self._warmup_filter(prices)
        elif new_price is not None and self.is_initialized:
            kf_result = self._update_filter(new_price)
        elif prices is not None:  # Re-warmup
            self.is_initialized = False
            kf_result = self._warmup_filter(prices)
        else:
            raise ValueError("Invalid args")

        # Merge results
        kf_result["tunneling_prob"] = tunneling_prob
        return kf_result

    @tracer.start_as_current_span("physics_warmup_filter")
    def _warmup_filter(self, prices: List[float]) -> Dict[str, float]:
        """
        Warmup Kalman Filter with historical data.
        Applies fractional differentiation for stationarity.
        """
        if len(prices) < 10:
            logger.error("PhysicsService: Insufficient warmup data (<10 bars)")
            return {"velocity": 0.0, "acceleration": 0.0}

        # Reset Kalman Filter
        self.kf = KinematicKalmanFilter()

        # Fractional Differentiation for stationarity
        try:
            stationary_series = FractalMemory.frac_diff(prices, d=0.4)
        except Exception as e:
            logger.error(f"PhysicsService: FracDiff failed: {e}")
            stationary_series = prices  # Fallback to raw

        # Replay history through filter
        final_estimate = None
        for measurement in stationary_series:
            final_estimate = self.kf.update(measurement)

        # Mark as initialized
        self.is_initialized = True
        self.last_price = prices[-1]

        if final_estimate:
            logger.info(
                f"PhysicsService: Warmup complete - "
                f"v={final_estimate.velocity:.4f}, a={final_estimate.acceleration:.4f}"
            )
            return {
                "velocity": final_estimate.velocity,
                "acceleration": final_estimate.acceleration,
            }
        else:
            return {"velocity": 0.0, "acceleration": 0.0}

    def _update_filter(self, new_price: float) -> Dict[str, float]:
        """
        Incrementally update Kalman Filter with single new price.
        Continues from previous state (preserves covariance).
        """
        # Calculate return for stationarity
        if self.last_price is None or self.last_price == 0:
            measurement = 0.0
        else:
            # Use log return for better stationarity
            measurement = np.log(new_price / self.last_price)

        # Update filter with new measurement
        estimate = self.kf.update(measurement)
        self.last_price = new_price

        return {
            "velocity": estimate.velocity,
            "acceleration": estimate.acceleration,
        }

    def reset_filter(self):
        """
        Explicitly reset Kalman Filter state.
        Use when market regime changes significantly.
        """
        logger.warning("PhysicsService: Explicit filter reset requested")
        self.kf = KinematicKalmanFilter()
        self.is_initialized = False
        self.last_price = None

    @tracer.start_as_current_span("physics_analyze_regime")
    def analyze_regime(self, price_history: List[float]) -> Dict[str, Any]:
        """
        Analyze Market Regime using Heavy Tail Statistics (Hill Estimator).

        Args:
            price_history: Chronological price history (will calculate returns internally).

        Returns:
            {
                'alpha': float,  # Tail index
                'regime': str    # 'Gaussian' | 'Lévy Stable' | 'Critical'
            }
        """
        try:
            # Validate input
            if len(price_history) < 20:  # Need minimum data for Hill estimator
                logger.warning(
                    f"PhysicsService: Insufficient history for regime analysis ({len(price_history)} bars)"
                )
                return {"alpha": 3.0, "regime": "Gaussian"}  # Safe default

            # Calculate percentage returns: (p[i] - p[i-1]) / p[i-1]
            returns = [
                (price_history[i] - price_history[i - 1]) / price_history[i - 1]
                for i in range(1, len(price_history))
                if price_history[i - 1] != 0  # Avoid division by zero
            ]

            if len(returns) < 20:
                logger.warning("PhysicsService: Too few valid returns")
                return {"alpha": 3.0, "regime": "Gaussian"}

            # Calculate Alpha (Tail Index)
            alpha = HeavyTailEstimator.hill_estimator(returns)

            # Detect Regime
            regime = HeavyTailEstimator.detect_regime(alpha)

            # Set span attributes
            span = trace.get_current_span()
            span.set_attribute("physics.alpha", alpha)
            span.set_attribute("physics.regime", regime)
            span.set_attribute("physics.sample_size", len(price_history))

            logger.debug(f"PhysicsService: Regime α={alpha:.2f}, regime={regime}")

            # Record metrics
            business_metrics.alpha_tail.set(alpha, {"regime": regime})

            return {"alpha": alpha, "regime": regime}

        except Exception as e:
            logger.error(f"PhysicsService: Regime analysis failed: {e}", exc_info=True)
            return {"alpha": 3.0, "regime": "Gaussian"}  # Safe default

    @tracer.start_as_current_span("physics_calculate_hurst")
    def calculate_hurst_and_mode(self, price_history: List[float]) -> Dict[str, Any]:
        """
        Calculate Hurst Exponent and determine optimal strategy mode.

        Hurst Interpretation (Mathematical Constitution v3.0 § 1.3):
        - H > 0.5: Persistent (Trending). Use momentum/breakout strategies.
        - H < 0.5: Anti-Persistent (Mean Reverting). Use reversion strategies.
        - H = 0.5: Random Walk. No edge.

        Args:
            price_history: List of historical prices

        Returns:
            {
                "hurst": float,           # Hurst exponent (0.0 - 1.0)
                "strategy_mode": str,     # "TREND" or "REVERSION" or "NEUTRAL"
                "persistence": str        # Human-readable interpretation
            }
        """
        span = trace.get_current_span()

        try:
            if len(price_history) < 50:
                logger.warning("PhysicsService: Insufficient data for Hurst (need 50+)")
                return {
                    "hurst": 0.5,
                    "strategy_mode": "NEUTRAL",
                    "persistence": "Insufficient Data",
                }

            # Calculate Hurst using R/S Analysis
            hurst = FractalMemory.calculate_hurst(price_history)

            # Determine strategy mode and persistence type
            if hurst > 0.55:  # Buffer around 0.5 for robustness
                strategy_mode = "TREND"
                persistence = "Persistent (Trending)"
            elif hurst < 0.45:
                strategy_mode = "REVERSION"
                persistence = "Anti-Persistent (Mean Reverting)"
            else:
                strategy_mode = "NEUTRAL"
                persistence = "Random Walk"

            # Set span attributes
            span.set_attribute("physics.hurst", hurst)
            span.set_attribute("physics.strategy_mode", strategy_mode)
            span.set_attribute("physics.sample_size", len(price_history))

            logger.info(
                f"PhysicsService: Hurst={hurst:.3f}, Mode={strategy_mode}, {persistence}"
            )

            # Record metrics
            business_metrics.hurst_exponent.set(hurst, {"symbol": "global"})
            business_metrics.strategy_mode_duration.record(1.0, {"mode": strategy_mode})

            return {
                "hurst": float(hurst),
                "strategy_mode": strategy_mode,
                "persistence": persistence,
            }

        except Exception as e:
            logger.error(f"PhysicsService: Hurst calculation error: {e}")
            # Safe fallback: assume neutral
            return {
                "hurst": 0.5,
                "strategy_mode": "NEUTRAL",
                "persistence": "Error - Defaulting to Neutral",
            }

    @tracer.start_as_current_span("physics_calculate_qho")
    def calculate_qho_levels(self, price_history: List[float]) -> Dict[str, Any]:
        """
        Calculate Quantum Harmonic Oscillator (QHO) Energy Levels.
        Constitution v3.0 § 3.2: Price in Mean Reversion is a particle in quadratic potential.
        Energy Levels E_n = h*w*(n + 1/2) imply discrete price levels.

        Mapping:
        x_n ~ sqrt(E_n) ~ sqrt(2n + 1)
        Levels = Mean ± Sigma * sqrt(2n + 1)
        """
        if len(price_history) < 20:
            return {"qho_levels": {}, "excitation_state": 0}

        try:
            # Use last 20 bars for local potential well
            window = price_history[-20:]
            mu = np.mean(window)
            sigma = np.std(window)

            if sigma == 0:
                return {"qho_levels": {}, "excitation_state": 0}

            # Calculate levels for n=0 to n=3
            levels = {}
            current_price = price_history[-1]
            min_dist = float("inf")
            nearest_n = 0

            for n in range(4):
                factor = np.sqrt(2 * n + 1)
                upper = mu + sigma * factor
                lower = mu - sigma * factor
                levels[f"n{n}_upper"] = upper
                levels[f"n{n}_lower"] = lower

                # Check excitation state (nearest level)
                dist_up = abs(current_price - upper)
                dist_down = abs(current_price - lower)

                if dist_up < min_dist:
                    min_dist = dist_up
                    nearest_n = n
                if dist_down < min_dist:
                    min_dist = dist_down
                    nearest_n = n

            return {
                "qho_levels": levels,
                "excitation_state": nearest_n,
                "zero_point_energy": mu,
            }

        except Exception as e:
            logger.error(f"PhysicsService: QHO calculation error: {e}")
            return {"qho_levels": {}, "excitation_state": 0}

    def reset(self):
        """
        Reset Kalman Filter state.
        Call this when starting a new symbol or after long pauses.
        """
        logger.info("PhysicsService: Resetting Kalman Filter")
        self.kf = KinematicKalmanFilter()
        self.is_initialized = False
        self.last_price = None
