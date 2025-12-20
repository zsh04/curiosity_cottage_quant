import pytest
from datetime import datetime
from app.services.soros import SorosService
from app.core.models import ForceVector, Side


class TestSorosReflexivity:
    @pytest.fixture
    def meister(self):
        return SorosService()

    @pytest.fixture
    def base_vector(self):
        return {
            "timestamp": datetime.now(),
            "symbol": "BTC-USD",
            "mass": 1000.0,
            "momentum": 100.0,
            "friction": 0.1,
            "entropy": 0.1,
            "nash_dist": 0.0,
            "alpha_coefficient": 2.5,
            "price": 100000.0,
        }

    def test_gate_1_alpha_veto(self, meister, base_vector):
        """Case A: Alpha <= 2.0 -> HOLD."""
        base_vector["alpha_coefficient"] = 1.0  # Fat tails / Infinite Variance
        force = ForceVector(**base_vector)

        signal = meister.apply_reflexivity(force)

        assert signal.side == Side.HOLD
        assert signal.meta["veto"] == "ALPHA_TOO_LOW"

    def test_gate_2_chaos_veto(self, meister, base_vector):
        """Case C: Entropy > 0.8 -> HOLD."""
        base_vector["entropy"] = 0.9  # Pure Randomness
        force = ForceVector(**base_vector)

        signal = meister.apply_reflexivity(force)

        assert signal.side == Side.HOLD
        assert signal.meta["veto"] == "CHAOS_DETECTED"

    def test_gate_3_buy_signal(self, meister, base_vector):
        """Case B: High Alpha, Low Entropy, Mom > 0, Nash < 2.0 -> BUY."""
        # Setup: Valid buy conditions
        base_vector["alpha_coefficient"] = 2.5
        base_vector["entropy"] = 0.1
        base_vector["momentum"] = 100.0
        base_vector["nash_dist"] = 0.5  # Not overbought ( < 2.0)

        force = ForceVector(**base_vector)

        signal = meister.apply_reflexivity(force)

        assert signal.side == Side.BUY
        assert signal.strength == 1.0
        assert signal.symbol == "BTC-USD"

    def test_gate_3_sell_signal(self, meister, base_vector):
        """Extra: Valid Sell."""
        base_vector["momentum"] = -100.0
        base_vector["nash_dist"] = -0.5  # Not oversold ( > -2.0)

        force = ForceVector(**base_vector)

        signal = meister.apply_reflexivity(force)

        assert signal.side == Side.SELL
        assert signal.strength == 1.0
