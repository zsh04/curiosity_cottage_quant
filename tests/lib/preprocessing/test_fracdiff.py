import pytest
import numpy as np
import pandas as pd
from app.lib.preprocessing.fracdiff import FractionalDifferentiator


class TestFractionalDifferentiator:
    def test_weights_calculation(self):
        """
        Test that weights are calculated correctly.
        For d=1, weights should be [1, -1, 0, 0...] approx.
        """
        fd = FractionalDifferentiator(threshold=1e-5)
        # For d=1, w0=1, w1=-1, w2=0...
        weights_d1 = fd.get_weights(d=1.0, size=10)

        # weights are returned reversed (oldest to newest for convolution)
        # So last element is w0 = 1, second to last is w1 = -1
        assert np.isclose(weights_d1[-1], 1.0)
        assert np.isclose(weights_d1[-2], -1.0)

        # Test Sum of weights for d=0 should be 1 (w0=1, others 0)
        weights_d0 = fd.get_weights(d=0.0, size=10)
        assert np.isclose(np.sum(weights_d0), 1.0)

        # Test Sum of weights for d=1 should be 0 (approx, as it's an infinite series)
        # w = (1-L)^d = 1 - dL + ...
        # At d=1, sum should converge to 0
        assert np.abs(np.sum(weights_d1)) < 0.1

    def test_stationarity_improvement(self):
        """
        Test that it can find a d < 1 for a stationary-ish series,
        or d close to 1 for a random walk.
        """
        np.random.seed(42)
        n = 1000

        # 1. Create a Mean Reverting Series (White Noise)
        # d should be close to 0
        mean_reverting = pd.Series(np.random.normal(0, 1, n))
        fd = FractionalDifferentiator()
        d_mr, _ = fd.find_min_d(mean_reverting)

        assert d_mr == 0.0  # Already stationary

        # 2. Create a Random Walk (Geometric Brownian Motion log price)
        # d should be needed
        random_walk = pd.Series(np.cumsum(np.random.normal(0, 1, n)))
        d_rw, diff_rw = fd.find_min_d(random_walk, p_value_threshold=0.05)

        # It usually requires some differencing
        assert d_rw > 0.0

        # But hopefully preserves some memory (d might not be exactly 1.0 if we allow p<0.05)
        # Note: Pure random walk is I(1), so theoretical d=1.
        # But finite samples often pass ADF with d < 1.

    def test_memory_preservation(self):
        """
        Test that we are not just returning empty series or losing all data.
        """
        np.random.seed(42)
        # Linear trend + noise
        ts = pd.Series(np.linspace(0, 10, 500) + np.random.normal(0, 0.1, 500))

        fd = FractionalDifferentiator()
        d, transformed = fd.find_min_d(ts)

        assert len(transformed) > 0
        assert not transformed.isna().all()
