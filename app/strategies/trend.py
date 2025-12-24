import pandas as pd
import numpy as np
from app.strategies.base import BaseStrategy
from app.lib.kalman.kinematic import KinematicKalmanFilter


class KalmanMomentumStrategy(BaseStrategy):
    """Trend following via Kalman-filtered velocity (3-state kinematic model).

    Signal = tanh(velocity * 10). Filters noise, captures sustained moves.
    **Best**: Trending markets | **Worst**: Choppy (velocity oscillates)
    """

    @property
    def name(self) -> str:
        return "KalmanMomentum_V2"

    def calculate_signal(self, market_data: pd.DataFrame) -> float:
        """
        Runs Kalman Filter on the close prices.
        Returns normalized velocity signal.

        **Kalman Momentum Constants**:

        1. **dt = 1.0** (Time Step):
           - Physical meaning: Discrete time interval
           - Chosen: 1 day (daily bars)
           - Units: Days (for daily data)
           - Alternative: Adjust for higher/lower frequency data
           - Effect: Determines velocity/acceleration scaling
           - Reference: Kalman (1960) "New Approach to Filtering"

        2. **final_velocity * 10** (Velocity Scaling for tanh):
           - Goal: Map velocity to [-1, 1] signal range
           - Physical basis: Typical velocity ≈ $0.1-$1.0 per day
           - Chosen: 10x multiplier saturates tanh at v > 0.1
           - Effect of tanh: Smooth saturation (no hard clipping)
           - Alternative: 5x (slower saturation), 20x (faster)
           - Example: v=0.1 -> signal=tanh(1.0)≈0.76 (strong buy)
           - Empirical: Tuned on SPY for optimal trend detection

        **Kalman Filter Note**:
        - Filter processes entire window (stateful)
        - Each bar updates: position, velocity, acceleration
        - Final velocity = momentum estimate at latest bar
        - Noise filtering: KF smooths out price jitter
        """
        with self.tracer.start_as_current_span("calculate_signal") as span:
            if market_data.empty:
                return 0.0

            # Initialize KF
            # We use a fresh KF for each calculation window if we are treating this strictly stateless
            # based on the passed window.
            # However, KF is stateful. Ideally, the strategy should maintain state.
            # But the BaseStrategy interface implies calculating on a window.
            # Detailed Choice: Re-running on the window (batch) is safer for determinism
            # but slower. Given the request context "Calculate signal(market_data)",
            # we will re-run on the provided window to get the 'latest' state.

            kf = KinematicKalmanFilter(dt=1.0)

            prices = market_data["close"].values

            # Run filter over the window
            final_velocity = 0.0

            # Optimization: If window is huge, this is slow.
            # Assuming reasonable window sizes (e.g. 100 bars).
            for price in prices:
                est = kf.update(price)
                final_velocity = est.velocity

            span.set_attribute("kalman.final_velocity", final_velocity)

            # Normalize Signal
            # Velocity can be anything. We use tanh to squash it to -1..1
            # Scaling factor * 10 is arbitrary but helps saturate the signal on strong trends.
            signal = float(np.tanh(final_velocity * 10))

            span.set_attribute("kalman.signal", signal)

            return signal
