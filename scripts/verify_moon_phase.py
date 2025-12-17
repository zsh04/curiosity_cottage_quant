import unittest
from unittest.mock import MagicMock, patch
import sys
from datetime import datetime

# 1. Mock dependencies
sys.modules["pandas"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["opentelemetry"] = MagicMock()
sys.modules["opentelemetry.trace"] = MagicMock()

# 2. Import Strategy
# We need to make sure BaseStrategy can be imported
# app.strategies.base imports pandas and opentelemetry.trace, which are now mocked.
from app.strategies.moon_phase import MoonPhaseStrategy


class TestMoonPhase(unittest.TestCase):
    def setUp(self):
        self.strategy = MoonPhaseStrategy()

    def test_calculate_phase_logic(self):
        """
        Verify math using standard datetime objects.
        REF_NEW_MOON is datetime(2000, 1, 6, 18, 14)
        Synodic Month = 29.53058867 days
        """
        # Test Case 1: The Reference New Moon itself
        ref_date = datetime(2000, 1, 6, 18, 14)
        phase = self.strategy.calculate_phase(ref_date)
        self.assertAlmostEqual(phase, 0.0, places=4)

        # Test Case 2: Exactly one synodic month later (Next New Moon)
        next_moon = (
            ref_date + (datetime(2000, 2, 1, 0, 0) - datetime(2000, 1, 1, 0, 0)) * 0
        )  # timedelta logic is tricky with floats.
        # Let's use total_seconds logic inverse.

        # Manually verify a known date: Jan 11, 2024 11:57 UTC (New Moon)
        # Delta from Ref:
        target = datetime(2024, 1, 11, 11, 57)
        phase = self.strategy.calculate_phase(target)

        # We expect phase to be close to 0.0 or 1.0
        # Phase is cyclic [0, 1). 0.99 is close to 0.0.
        # Let's see what we get.
        print(f"Jan 11 2024 Phase: {phase}")

        # Check if it's within "New Moon" range (0.98-1.0 or 0.0-0.02)
        is_new_moon = (phase >= 0.98) or (phase <= 0.02)
        self.assertTrue(is_new_moon, f"Expected New Moon, got phase {phase}")

    def test_calculate_signal_full_moon(self):
        # Known Full Moon: Jan 25, 2024 17:54 UTC
        target = datetime(2024, 1, 25, 17, 54)
        phase = self.strategy.calculate_phase(target)
        print(f"Jan 25 2024 Phase: {phase}")

        # Check if it's Full Moon (0.48 - 0.52)
        self.assertTrue(0.48 <= phase <= 0.52, f"Expected Full Moon, got {phase}")

        # Test Signal Generation
        # Mock DataFrame input
        mock_df = MagicMock()
        mock_df.empty = False
        # Mock index[-1] to return our target datetime
        # We use a PropertyMock or just configure return value if it's a method call,
        # but index is a property. simpler to mock the attribute access.
        type(mock_df).index = MagicMock()
        mock_df.index.__getitem__.return_value = target  # for index[-1]

        # Since index is usually accessed as df.index, we set it on the instance
        mock_df.index = [target]

        signal = self.strategy.calculate_signal(mock_df)
        self.assertEqual(signal, -1.0)  # Sell


if __name__ == "__main__":
    unittest.main()
