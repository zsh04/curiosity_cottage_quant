import numpy as np
import pandas as pd
from typing import Union, Tuple, Optional


class HeavyTailEstimator:
    """
    Implements Heavy Tail statistics to detect the Probabilistic Regime of the market.

    Core Concept:
    Markets alternate between two regimes:
    1. Gaussian (Alpha > 3.0): Mean-reverting, finite variance. Safe for standard models.
    2. Levy Stable (1.0 < Alpha < 2.0): Infinite variance, trending, black swan prone.
       Standard models fail here. Momentum dominates.
    """

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
    def detect_regime(alpha: float) -> str:
        """
        Classifies the regime based on the Alpha.

        Alpha > 2.0: 'Gaussian' (Finite Variance)
        1.0 < Alpha <= 2.0: 'Levy' (Infinite Variance / Heavy Tail)
        Alpha <= 1.0: 'Cauchy' (Undefined Mean - Extreme Risk)
        """
        if alpha > 2.0:
            return "GAUSSIAN"
        elif alpha > 1.0:
            return "LEVY"
        else:
            return "CAUCHY"
