import pytest
import numpy as np
from app.services.feynman import FeynmanService


class TestFeynmanService:
    @pytest.fixture
    def wolf(self):
        """Initializes The Wolf with a smaller window for testing."""
        return FeynmanService(window_size=20)

    def test_buffer_mechanics(self, wolf):
        """Verifies the ring buffer rotation and zero-allocation logic."""
        # Fill buffer
        for i in range(15):
            wolf.update_buffer(price=float(i), volume=100.0, trade_count=1)

        # Check current implementation details
        # Since we use np.roll(-1) and insert at -1:
        # The last element should be 14.0
        assert wolf.prices[-1] == 14.0
        # The element before it should be 13.0
        assert wolf.prices[-2] == 13.0
        # The first element (index 0) should be 5.0 (since window is 10, 0-4 rolled off)
        assert wolf.prices[0] == 5.0

        assert wolf.is_filled is True
        assert wolf.cursor == 15

    def test_mass_calculation(self, wolf):
        """Verifies Mass = Volume * CLV."""
        # Scenario: Trending Up Candle
        # Low=10, High=20, Close=18.
        # Range = 10.
        # CLV = ((18-10) - (20-18)) / 10 = (8 - 2) / 10 = 0.6
        # Volume = 100
        # Mass should be 60.

        # We need to fill the buffer such that Min is 10, Max is 20.
        wolf.update_buffer(10.0, 100.0, 1)  # Low
        wolf.update_buffer(20.0, 100.0, 1)  # High
        wolf.update_buffer(18.0, 100.0, 1)  # Current

        forces = wolf.calculate_forces()

        # Mass calculation depends on the ENTIRE buffer min/max.
        # In this 3-tick buffer: Min=10, Max=20. Current=18.
        # CLV = 0.6. Vol=100. Mass=60.
        assert forces["mass"] == pytest.approx(60.0, abs=0.1)

    def test_friction_calculation(self, wolf):
        """Verifies Friction = Trades / Volume."""
        # Trades=50, Vol=100 -> Friction=0.5
        # Need > 1 tick for global check, though friction is instantaneous.
        # Code requires cursor >= 2.
        wolf.update_buffer(100.0, 100.0, 50)
        wolf.update_buffer(100.0, 100.0, 50)  # Add second tick
        forces = wolf.calculate_forces()
        assert forces["friction"] == 0.5

    def test_entropy_chaos(self, wolf):
        """Verifies Entropy detection on random vs constant data."""
        # 1. Constant Data -> Zero Entropy
        for _ in range(10):
            wolf.update_buffer(100.0, 100.0, 1)

        forces = wolf.calculate_forces()
        # Returns will be 0. Entropy of a single bin is 0.
        # Implementation detail: np.diff(np.log(constant)) -> zeros.
        # Histogram of zeros -> all in one bin -> Entropy 0.
        assert forces["entropy"] == pytest.approx(0.0)

    def test_nash_regime(self, wolf):
        """Verifies Nash Equilibrium Distance."""
        # Create a distribution with a clear mode at 100
        # Need > 10 ticks. Let's do 15.
        for _ in range(15):
            wolf.update_buffer(100.0, 100.0, 1)
        # Add an outlier
        wolf.update_buffer(110.0, 100.0, 1)

        forces = wolf.calculate_forces()

        # Mode should be ~100. Current is 110.
        # It's distant from mode. Nash Distance should be high.
        assert forces["nash_distance"] > 1.0
        assert forces["regime"] == "TRENDING"
