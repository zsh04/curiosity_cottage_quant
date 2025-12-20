import pytest
import numpy as np
from datetime import datetime
from app.services.feynman import FeynmanService
from app.core.models import ForceVector


class TestFeynmanIntegration:
    @pytest.fixture
    def wolf(self):
        return FeynmanService(window_size=1000)

    def test_warmup_phase(self, wolf):
        """Test 1: Feed 1000 ticks and verify warmup."""
        assert not wolf.is_filled

        # Feed 999
        for i in range(999):
            wolf.update_buffer(100.0, 100.0, 1)
        assert not wolf.is_filled

        # Feed 1000th
        wolf.update_buffer(100.0, 100.0, 1)
        assert wolf.is_filled
        assert wolf.cursor == 1000

    def test_physics_sine_wave(self, wolf):
        """Test 2: Feed a Sine Wave to generate dynamic forces."""
        # Generate 200 ticks of a sine wave
        # End at 4.5pi (Peak) so CLV is 1.0, avoiding 0.0 mass
        x = np.linspace(0, 4.5 * np.pi, 200)
        prices = 100 + 10 * np.sin(x)

        for p in prices:
            wolf.update_buffer(price=p, volume=1000.0, trade_count=50)

        forces = wolf.calculate_forces()

        assert forces["mass"] != 0.0
        assert forces["momentum"] != 0.0
        # Friction = 50 / 1000 = 0.05
        assert forces["friction"] == pytest.approx(0.05)
        # Nash Dist should be non-zero as Sine wave isn't a flat line
        assert forces["nash_dist"] != 0.0

        # Validate Contract
        vector = ForceVector(timestamp=datetime.now(), symbol="SINE", **forces)
        assert vector.mass == forces["mass"]

    def test_entropy_chaos(self, wolf):
        """Test 3: Feed random noise."""
        np.random.seed(42)
        prices = np.random.normal(100, 5, 200)

        for p in prices:
            wolf.update_buffer(p, 1000.0, 10)

        forces = wolf.calculate_forces()

        # Random noise should have higher entropy than constant
        assert forces["entropy"] > 0.0
