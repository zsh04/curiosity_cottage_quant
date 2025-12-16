"""
Fractional Differentiation Implementation.
Based on "Advances in Financial Machine Learning" (Lopez de Prado, 2018).
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
from statsmodels.tsa.stattools import adfuller


class FractionalDifferentiator:
    """
    Implements Fractional Differentiation to achieve stationarity while preserving memory.
    """

    def __init__(self, threshold: float = 1e-5):
        """
        Args:
            threshold: Cutoff for weight coefficients. Weights below this are ignored
                      to strictly limit the lookback window (preventing data leakage).
        """
        self.threshold = threshold

    def get_weights(self, d: float, size: int) -> np.ndarray:
        """
        Calculate weights for fractional differentiation using binomial expansion.
        w_k = -w_{k-1} * (d - k + 1) / k
        """
        # w_0 = 1
        w = [1.0]
        for k in range(1, size):
            w_k = -w[-1] * (d - k + 1) / k
            if abs(w_k) < self.threshold:
                break
            w.append(w_k)

        return np.array(w[::-1])  # Reverse for dot product (oldest to newest)

    def frac_diff(self, series: pd.Series, d: float) -> pd.Series:
        """
        Apply fractional differentiation to a series.
        """
        # 1. Get weights
        # We perform the calculation using a window size equal to the series length
        # but the effective window is limited by the threshold in get_weights.
        weights = self.get_weights(d, len(series))

        # 2. Apply weights via rolling window (correlation/convolution)
        # Note: This is an efficient vectorized implementation.
        # However, for massive series, we might want a fixed window size.
        # Here we use the full available history up to the weight cutoff.

        # We need at least len(weights) data points to compute the first value
        if len(series) < len(weights):
            return pd.Series(index=series.index, dtype=float)

        # Standard implementation matching Lopez de Prado
        # But optimized with pandas rolling/apply is tricky with variable weights.
        # Iterative approach is clearer for now, or numpy convolution.

        # Using numpy convolution
        # series values: [p_0, p_1, ..., p_T]
        # weights: [w_k, ..., w_1, w_0] (reversed in get_weights)

        values = series.dropna().values
        if len(values) == 0:
            return pd.Series(dtype=float)

        # Convolve "valid" mode returns only points where signals overlap completely
        # which means we lose the first len(weights)-1 points.
        diff = np.convolve(values, weights, mode="valid")

        # Re-align index
        # The last value of diff corresponds to the last value of series.
        # diff indexes are [0 ... T - (W-1)]
        # series indexes are [0 ... T]
        # We want to map diff[-1] -> series[-1]

        # Result series
        result_series = pd.Series(data=diff, index=series.index[len(weights) - 1 :])

        return result_series

    def find_min_d(
        self, series: pd.Series, p_value_threshold: float = 0.05
    ) -> Tuple[float, pd.Series]:
        """
        Find the minimum fractional dimension 'd' that makes the series stationary.
        Searches d in [0.0, 1.0] with steps of 0.05.

        Returns:
            Tuple(min_d, differentiated_series)
        """
        # Clean infinite/NaNs
        clean_series = series.replace([np.inf, -np.inf], np.nan).dropna()

        best_d = 1.0
        best_series = clean_series.diff().dropna()  # Fallback to d=1

        # Iterate 0.0 to 1.0
        # We start checking from 0 up. The first one that passes is our minimal d.
        for d in np.linspace(0.0, 1.0, 21):  # 0.0, 0.05, 0.1 ... 1.0
            if d == 0:
                diff_series = clean_series
            else:
                diff_series = self.frac_diff(clean_series, d)

            # Check for stationarity
            # Need strict dropna because FracDiff introduces NaNs at the start
            check_series = diff_series.dropna()

            # ADF Test requires some data points
            if len(check_series) < 20:
                # Not enough data after differencing to test.
                # If d is small, we should have data. If d is large, we check weights.
                continue

            try:
                # adfuller returns (adf_stat, pvalue, usedlag, nobs, crit_values, icbest)
                result = adfuller(check_series, maxlag=1, regression="c", autolag=None)
                p_value = result[1]

                if p_value < p_value_threshold:
                    best_d = d
                    best_series = diff_series
                    break
            except Exception:
                # If ADF fails (e.g. SVD convergence), skip
                continue

        return float(best_d), best_series

    def transform(self, series: pd.Series) -> pd.Series:
        """
        Public API: Automatically transform the series to be stationary.
        """
        d, new_series = self.find_min_d(series)
        return new_series
