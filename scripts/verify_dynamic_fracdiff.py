import unittest
from unittest.mock import MagicMock, patch
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock dependencies before importing app modules
sys.modules["numpy"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["scipy"] = MagicMock()
sys.modules["scipy.stats"] = MagicMock()
sys.modules["statsmodels"] = MagicMock()
sys.modules["statsmodels.tsa"] = MagicMock()
sys.modules["statsmodels.tsa.stattools"] = MagicMock()

# Mock App dependencies
sys.modules["app.core.config"] = MagicMock()
sys.modules["app.agent.state"] = MagicMock()

# Import target module
# We need to ensure FractalMemory can be imported even with mocks
from app.lib.memory import FractalMemory


class TestDynamicFracDiff(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        self.mock_adfuller = MagicMock()
        # Patch adfuller where it is imported in memory.py
        # optimizing: since memory.py does "from statsmodels... import adfuller" inside the method or top level?
        # It does import inside the method try/except.
        # But we mocked sys.modules["statsmodels.tsa.stattools"], so the import should get the mock.
        self.mock_stats_module = sys.modules["statsmodels.tsa.stattools"]
        self.mock_stats_module.adfuller = self.mock_adfuller

        # Mock numpy array behavior for valid_data check
        self.mock_np = sys.modules["numpy"]
        self.mock_np.array.side_effect = lambda x: MagicMock(
            __len__=lambda self: 100,
            __getitem__=lambda self, idx: MagicMock(
                __len__=lambda s: 100
            ),  # filtered array
        )

        # Mock FractalMemory.frac_diff to return a dummy list
        # We need to patch the static method or just rely on the mock if we haven't imported real underlying libs.
        # But FractalMemory IS imported. We want to test finding d, so we ideally want frac_diff to run or be mocked.
        # Since frac_diff depends on pandas/numpy which are mocked, it's safer to mock frac_diff too
        # unless we want to test the loop logic specifically.
        # We WANT to test the loop logic.

        # Let's mock frac_diff to return something simple to avoid complex pandas mocking
        self.original_frac_diff = FractalMemory.frac_diff
        FractalMemory.frac_diff = MagicMock(return_value=[1.0] * 100)

    def tearDown(self):
        FractalMemory.frac_diff = self.original_frac_diff

    def test_optimal_d_low(self):
        """Test finding a low d (0.1)"""
        # Setup adfuller to pass (p < 0.05) immediately
        # Returns: (adf, pvalue, usedlag, nobs, crit, icbest)
        self.mock_adfuller.return_value = (-5.0, 0.01, 0, 100, {}, 0)

        series = [100.0] * 100
        d, diff_series = FractalMemory.find_optimal_d(series)

        self.assertEqual(d, 0.1)
        # Should stop after first call
        self.assertEqual(FractalMemory.frac_diff.call_count, 1)

    def test_optimal_d_high(self):
        """Test finding a higher d (0.4)"""
        # Setup adfuller to fail for first 3 calls (0.1, 0.2, 0.3) then pass at 0.4
        # p-values: 0.9, 0.8, 0.7, 0.04
        self.mock_adfuller.side_effect = [
            (-1.0, 0.9, 0, 100, {}, 0),  # d=0.1
            (-1.0, 0.8, 0, 100, {}, 0),  # d=0.2
            (-1.0, 0.7, 0, 100, {}, 0),  # d=0.3
            (-5.0, 0.04, 0, 100, {}, 0),  # d=0.4
        ]

        series = [100.0] * 100
        d, diff_series = FractalMemory.find_optimal_d(series)

        self.assertAlmostEqual(d, 0.4)
        self.assertEqual(FractalMemory.frac_diff.call_count, 4)

    def test_fallback(self):
        """Test fallback to d=0.4 if all fail"""
        # Setup adfuller to always fail
        self.mock_adfuller.return_value = (-1.0, 0.99, 0, 100, {}, 0)

        series = [100.0] * 100
        d, diff_series = FractalMemory.find_optimal_d(series)

        # Expect fallback d=0.4 (as coded in implementation)
        self.assertEqual(d, 0.4)
        # Should iterate 0.1 to 1.0 (10 calls) + 1 fallback call = 11?
        # Implementation: loop 1..11. if finish loop, call frac_diff(0.4) and return.
        # Wait, loop is range(1, 11) -> 1..10. 10 calls.
        # Then fallback calls frac_diff(d=0.4). So 11 calls.
        self.assertEqual(FractalMemory.frac_diff.call_count, 11)


if __name__ == "__main__":
    unittest.main()
