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
    """
    Implements Heavy Tail statistics to detect the Probabilistic Regime of the market.

    Core Concept:
    Markets alternate between two regimes:
    1. Gaussian (Alpha > 3.0): Mean-reverting, finite variance. Safe for standard models.
    2. Levy Stable (1.0 < Alpha < 2.0): Infinite variance, trending, black swan prone.
       Standard models fail here. Momentum dominates.
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
        return self.hill_estimator(np.array(self.returns))

    @staticmethod
    def hill_estimator(
        data: Union[pd.Series, np.ndarray], tail_percentile: float = 0.05
    ) -> float:
        """
        Calculates the Hill Estimator for the tail exponent (Alpha).

        Formula:
        Alpha = 1 / ( (1/k) * Sum( ln(X_i / X_min) ) )

        Args:
            data: Financial time series (returns or prices).
            tail_percentile: The percentage of data to consider as the "tail" (e.g., top 5%).

        Returns:
            float: The estimated Alpha (tail exponent).
        """
        if isinstance(data, pd.Series):
            data = data.values

        # We look at the magnitude of returns for heavy tails
        abs_data = np.abs(data)

        # Sort data descending
        sorted_data = np.sort(abs_data)[::-1]

        n = len(sorted_data)
        k = int(n * tail_percentile)

        if k < 2:
            return 3.0  # Insufficient data for tail estimation, assume Gaussian default

        # Select the tail
        tail = sorted_data[:k]
        x_min = sorted_data[k]  # The threshold

        # Hill calc
        # ln(X_i / X_min) = ln(X_i) - ln(X_min)
        log_ratios = np.log(tail / x_min)
        hill_val = np.mean(log_ratios)

        if hill_val == 0:
            return 3.0

        alpha = 1.0 / hill_val
        return alpha

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
