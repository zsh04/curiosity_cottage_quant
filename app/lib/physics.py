"""
Heavy Tail & Regime Math.
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional


class Regime(Enum):
    GAUSSIAN = "Gaussian"
    LEVY_STABLE = "Lévy Stable"
    CRITICAL = "Critical"


@dataclass
class RegimeMetrics:
    alpha: float
    regime: Regime
    leverage_cap: float


class HeavyTailEstimator:
    """
    Estimates the tail index (alpha) of a distribution to detect infinite variance regimes.
    Uses the Hill Estimator.
    """

    @staticmethod
    def hill_estimator(returns: np.ndarray, tail_fraction: float = 0.05) -> float:
        """
        Calculate the Hill Estimator for the tail index alpha.

        Args:
            returns: Array of returns (positive and negative).
            tail_fraction: Fraction of the data to consider as the tail (k/n).

        Returns:
            alpha: The estimated tail index.
        """
        abs_returns = np.abs(returns)
        # Sort descending
        sorted_returns = np.sort(abs_returns)[::-1]
        n = len(sorted_returns)
        k = int(n * tail_fraction)

        if k < 2:
            # Not enough data for tail estimation, return a safe Gaussian proxy or raise?
            # Returning a high alpha (Gaussian) if insufficient data might be dangerous,
            # but for now let's assume valid data or return 3.0 (Gaussian boundary)
            return 3.0

        # Standard Hill Estimator Formula
        # alpha = 1 / ( (1/k) * sum( log(x_i / x_k) ) )
        # where x_i are the top k extreme values

        x_k = sorted_returns[k]  # The threshold value
        log_ratios = np.log(sorted_returns[:k] / x_k)
        hill_stat = np.mean(log_ratios)

        if hill_stat <= 1e-6:
            return 100.0  # Effectively infinite alpha (no tail)

        alpha = 1.0 / hill_stat
        return alpha

    @staticmethod
    def get_regime(alpha: float) -> RegimeMetrics:
        """
        Classify the regime based on the alpha value.
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


def expected_shortfall(returns: np.ndarray, confidence_level: float = 0.95) -> float:
    """
    Calculate the Expected Shortfall (CVaR) at a given confidence level.
    This is the average loss GIVEN that the loss is greater than the VaR.

    Returns a POSITIVE float representing the magnitude of the loss.
    """
    if len(returns) == 0:
        return 0.0

    cutoff_index = int((1 - confidence_level) * len(returns))
    if cutoff_index == 0:
        # If very few data points, essentially max loss
        cutoff_index = 1

    sorted_returns = np.sort(returns)  # Ascending: most negative first

    # The tail is the first 'cutoff_index' elements
    tail = sorted_returns[:cutoff_index]

    # ES is the average of these tail losses
    # We return positive magnitude
    es = -np.mean(tail)

    return max(0.0, es)
