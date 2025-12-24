import numpy as np
import pandas as pd
from typing import Union, Tuple, Optional, List
from enum import Enum
from dataclasses import dataclass


class Regime(str, Enum):
    GAUSSIAN = "Gaussian"
    LEVY_STABLE = "Lévy Stable"
    CRITICAL = "Critical"  # Replaces CAUCHY for consistency


@dataclass
class RegimeMetrics:
    alpha: float
    regime: Regime
    leverage_cap: float


def expected_shortfall(returns: np.ndarray, confidence_level: float = 0.95) -> float:
    """
    Calculate the Expected Shortfall (CVaR) at a given confidence level.
    """
    if len(returns) == 0:
        return 0.0

    cutoff_index = int((1 - confidence_level) * len(returns))
    if cutoff_index == 0:
        cutoff_index = 1

    sorted_returns = np.sort(returns)
    tail = sorted_returns[:cutoff_index]
    es = -np.mean(tail)
    return float(max(0.0, es))


class HeavyTailEstimator:
    """Hill estimator for tail exponent (α) - detects infinite-variance regimes.

    Implements power law analysis to classify market regimes based on return distribution
    tail behavior. Critical for risk management when standard deviation becomes meaningless.

    **Theory**:
    Financial returns follow power law: P(X > x) ~ x^(-α)
    - **α > 3.0**: Gaussian regime (finite variance, standard models work)
    - **2.0 < α ≤ 3.0**: Lévy stable (heavy tails, momentum dominates)
    - **α ≤ 2.0**: Critical/Cauchy (infinite variance, BLACK SWAN zone)

    **Hill Estimator Formula**:
    ```
    α = 1 / [ (1/k) * Σ ln(X_i / X_min) ]
    ```
    Where k = tail sample size (adaptive: 10%/5%/3% based on n)

    **Adaptive Tail Sizing**:
    - n < 30: 10% (small sample stability)
    - 30 ≤ n < 500: 5% (medium samples)
    - n ≥ 500: 3% (large sample precision)
    - Minimum: 10 observations for reliability

    **Regime Classification & Leverage Caps**:
    - **Gaussian** (α > 3.0): 1.0x leverage (safe)
    - **Lévy** (2.0 < α ≤ 3.0): 0.5x leverage (caution)
    - **Critical** (α ≤ 2.0): 0.0x leverage (HALT trading)

    Attributes:
        window_size: Rolling window for alpha calculation
        returns: Circular buffer of return observations

    Example:
        >>> estimator = HeavyTailEstimator(window_size=100)
        >>> estimator.update(return_val=0.02)
        >>> alpha = estimator.get_current_alpha()
        >>> regime = HeavyTailEstimator.get_regime(alpha)
        >>> print(regime.regime, regime.leverage_cap)  # "Critical", 0.0
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.returns: List[float] = []  # List to store returns

    def update(self, return_val: float):
        """Add a new return observation."""
        self.returns.append(return_val)
        if len(self.returns) > self.window_size:
            self.returns.pop(0)

    def get_current_alpha(self) -> float:
        """Calculate Alpha on the current window."""
        if len(self.returns) < 20:  # Minimum data check
            return 3.0  # Default Gaussian
        alpha, _ = self.hill_estimator(np.array(self.returns))
        return alpha

    def get_current_alpha_with_reliability(self) -> Tuple[float, str]:
        """Calculate Alpha and Reliability."""
        if len(self.returns) < 20:
            return 3.0, "Low"
        return self.hill_estimator(np.array(self.returns))

    @staticmethod
    def hill_estimator(
        data: Union[pd.Series, np.ndarray], tail_percentile: Optional[float] = None
    ) -> Tuple[float, str]:
        """
        Calculates the Hill Estimator for the tail exponent (Alpha).

        OPTIMIZATION: Uses adaptive tail size based on sample size for statistical stability.
        - Small samples (< 100): Use more data (10%)
        - Medium samples (100-500): Use 5%
        - Large samples (> 500): Use 3% for precision

        Formula:
        Alpha = 1 / ( (1/k) * Sum( ln(X_i / X_min) ) )

        Args:
            data: Financial time series (returns or prices).
            tail_percentile: Optional fixed percentile. If None, uses adaptive sizing.

        Returns:
            (alpha, reliability_score): Tuple of alpha and reliability string ("Low", "High").
        """
        if isinstance(data, pd.Series):
            data = data.values

        # We look at the magnitude of returns for heavy tails
        abs_data = np.abs(data)

        # Sort data descending
        sorted_data = np.sort(abs_data)[::-1]

        n = len(sorted_data)

        # Reliability Check (Task 4)
        reliability = "High" if n >= 500 else "Low"

        # ADAPTIVE TAIL SIZE for statistical robustness
        if tail_percentile is None:
            if n < 30:
                tail_percentile = 0.10  # 10% for small samples
            elif n < 500:
                tail_percentile = 0.05  # 5% for medium samples
            else:
                tail_percentile = 0.03  # 3% for large samples

        k = int(n * tail_percentile)

        # MINIMUM TAIL SIZE: Ensure at least 10 observations for reliability
        # Hill estimator becomes unreliable with very few tail samples
        min_tail_size = 10
        if k < min_tail_size:
            if n >= min_tail_size:
                k = min_tail_size
            else:
                # Not enough data for reliable estimation
                return 3.0, "Low"  # Default to Gaussian

        # Select the tail
        tail = sorted_data[:k]
        x_min = sorted_data[k]  # The threshold

        if x_min <= 0:
            # Avoid log of zero or negative
            return 3.0, "Low"

        # Hill calculation
        # ln(X_i / X_min) = ln(X_i) - ln(X_min)
        try:
            log_ratios = np.log(tail / x_min)
            hill_val = np.mean(log_ratios)
        except (RuntimeWarning, ValueError):
            return 3.0, "Low"

        if hill_val <= 0:
            return 3.0, "Low"

        alpha = 1.0 / hill_val

        # Sanity check: Alpha should be in reasonable range
        # Clamp to [0.5, 10.0] to avoid numerical instabilities
        alpha = np.clip(alpha, 0.5, 10.0)

        return float(alpha), reliability

    @staticmethod
    def get_regime(alpha: float) -> RegimeMetrics:
        """
        Classify the regime based on the Alpha.
        """
        if alpha > 3.0:
            return RegimeMetrics(alpha=alpha, regime=Regime.GAUSSIAN, leverage_cap=1.0)
        elif 2.0 < alpha <= 3.0:
            return RegimeMetrics(
                alpha=alpha, regime=Regime.LEVY_STABLE, leverage_cap=0.5
            )
        else:
            # alpha <= 2.0
            return RegimeMetrics(alpha=alpha, regime=Regime.CRITICAL, leverage_cap=0.0)

    @staticmethod
    def detect_regime(alpha: float) -> str:
        # Legacy/String wrapper
        return HeavyTailEstimator.get_regime(alpha).regime.value
