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

    def test_trinity_fusion(self, meister, base_vector):
        """Test the integration of Chronos Forecasts."""
        force = ForceVector(**base_vector)

        # 1. Missing Forecast -> Penalty
        meister.latest_forecast = None
        # Setup clean uptrend for physics
        force.momentum = 100.0
        force.nash_dist = 0.5

        signal = meister.apply_reflexivity(force)
        assert signal.side == Side.BUY
        assert signal.strength == 0.5
        assert signal.meta["warning"] == "NO_FORECAST_AVAILABLE"

        # 2. Agreement (Bullish) -> High Confidence
        from app.core.models import ForecastPacket

        meister.latest_forecast = ForecastPacket(
            timestamp=datetime.now(),
            symbol="BTC-USD",
            p10=90000.0,
            p50=105000.0,  # Higher than current price (100k)
            p90=110000.0,
            horizon=10,
            confidence=0.8,
        )

        signal = meister.apply_reflexivity(force)
        assert signal.side == Side.BUY
        assert signal.strength == 1.0
        assert signal.meta["confluence"] == "BULLISH_AGREEMENT"

        # 3. Divergence (Bearish Forecast vs Bullish Physics) -> VETO
        meister.latest_forecast.p50 = 95000.0  # Lower than current price (100k)

        signal = meister.apply_reflexivity(force)
        assert signal.side == Side.HOLD
        assert signal.strength == 0.0
        assert signal.meta["veto"] == "DIVERGENCE_FORECAST_BEARISH"
