import pytest
from datetime import datetime
from unittest.mock import AsyncMock
from app.services.soros import SorosService
from app.core.models import ForceVector, Side, ForecastPacket


class TestSorosReflexivity:
    @pytest.fixture
    def meister(self):
        service = SorosService()
        # Mock the debate to avoid network calls and return agreement by default
        service.conduct_debate = AsyncMock(
            return_value={
                "bull_argument": "Momentum is strong.",
                "bear_argument": "Risk is low.",
                "judge_verdict": "BUY",
                "confidence": 0.9,
            }
        )
        return service

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

    @pytest.mark.asyncio
    async def test_gate_1_alpha_veto(self, meister, base_vector):
        """Case A: Alpha <= 2.0 -> HOLD."""
        base_vector["alpha_coefficient"] = 1.0
        force = ForceVector(**base_vector)

        signal = await meister.apply_reflexivity_async(force)

        assert signal.side == Side.HOLD
        assert signal.meta["veto"] == "ALPHA_TOO_LOW"

    @pytest.mark.asyncio
    async def test_gate_2_chaos_veto(self, meister, base_vector):
        """Case C: Entropy > 0.8 -> HOLD."""
        base_vector["entropy"] = 0.9
        force = ForceVector(**base_vector)

        signal = await meister.apply_reflexivity_async(force)

        assert signal.side == Side.HOLD
        assert signal.meta["veto"] == "CHAOS_DETECTED"

    @pytest.mark.asyncio
    async def test_gate_3_buy_signal(self, meister, base_vector):
        """Case B: Valid Buy + Forecast + Judge Agreement."""
        # Setup: Agreeing Forecast
        meister.update_forecast(
            ForecastPacket(
                timestamp=datetime.now(),
                symbol="BTC-USD",
                p10=90.0,
                p50=110000.0,
                p90=120.0,
                horizon=10,
                confidence=1.0,
            )
        )

        # Setup: Valid buy conditions
        base_vector["alpha_coefficient"] = 2.5
        base_vector["entropy"] = 0.1
        base_vector["momentum"] = 100.0
        base_vector["nash_dist"] = 0.5

        force = ForceVector(**base_vector)

        signal = await meister.apply_reflexivity_async(force)

        assert signal.side == Side.BUY
        assert signal.strength == 1.0
        assert signal.meta["judge_verdict"] == "BUY"

    @pytest.mark.asyncio
    async def test_gate_5_judge_veto(self, meister, base_vector):
        """Case D: Physics/Quant say BUY, but Judge says HOLD."""
        # Mock Judge Disagreement
        meister.conduct_debate = AsyncMock(
            return_value={
                "bull_argument": "Trend up.",
                "bear_argument": "News is bad.",
                "judge_verdict": "HOLD",  # VETO
                "confidence": 0.8,
            }
        )

        # Setup: Agreeing Forecast
        meister.update_forecast(
            ForecastPacket(
                timestamp=datetime.now(),
                symbol="BTC-USD",
                p10=90.0,
                p50=110000.0,
                p90=120.0,
                horizon=10,
                confidence=1.0,
            )
        )

        base_vector["momentum"] = 100.0
        base_vector["nash_dist"] = 0.5

        force = ForceVector(**base_vector)

        signal = await meister.apply_reflexivity_async(force)

        assert signal.side == Side.HOLD
        assert signal.meta["veto"] == "JUDGE_OVERRULED"
