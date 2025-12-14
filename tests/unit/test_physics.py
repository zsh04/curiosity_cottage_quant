import pytest
import numpy as np
from lib.physics.heavy_tail import HeavyTailEstimator


class TestHeavyTailEstimator:
    def test_hill_estimator_gaussian(self):
        """
        Verify that Gaussian noise returns a high Alpha (typically > 3 or clipped to 3.0 in our logic).
        """
        np.random.seed(42)
        # Generate Gaussian noise
        data = np.random.normal(0, 1, 1000)

        alpha = HeavyTailEstimator.hill_estimator(data)

        # Our implementation clips/defaults to 3.0 if tail behavior isn't extreme or finite variance
        # Or returns a high value.
        # For pure Normal, the tail decays super fast, so hill estimator might be unstable or large.
        # Let's check if it classifies as Gaussian (> 2.0)

        assert alpha > 2.0, f"Gaussian data should have Alpha > 2.0, got {alpha}"
        assert HeavyTailEstimator.detect_regime(alpha) == "GAUSSIAN"

    def test_hill_estimator_pareto(self):
        """
        Verify that Pareto distributed data (Heavy Tail) returns an Alpha close to the true shape param.
        """
        np.random.seed(42)
        shape_param = 1.5  # Alpha = 1.5 (Levy Stable Regime)
        # Pareto distribution: X ~ Pareto(alpha)
        # numpy pareto returns x >= 1
        data = np.random.pareto(shape_param, 5000)

        alpha = HeavyTailEstimator.hill_estimator(data, tail_percentile=0.05)

        # Allow some estimation error margin
        assert 1.3 < alpha < 1.7, f"Expected Alpha ~ 1.5, got {alpha}"
        assert HeavyTailEstimator.detect_regime(alpha) == "LEVY"

    def test_detect_regime_logic(self):
        assert HeavyTailEstimator.detect_regime(3.5) == "GAUSSIAN"
        assert HeavyTailEstimator.detect_regime(1.5) == "LEVY"
        assert HeavyTailEstimator.detect_regime(0.8) == "CAUCHY"
