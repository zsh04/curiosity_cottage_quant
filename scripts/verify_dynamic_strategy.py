import sys
import os
import logging
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- AGGRESSIVE MOCKING ---
sys.modules["numpy"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["scipy"] = MagicMock()
sys.modules["scipy.stats"] = MagicMock()
sys.modules["langgraph"] = MagicMock()
sys.modules["langgraph.graph"] = MagicMock()

# Mock Internal Logic Components not under test
sys.modules["app.agent.graph"] = MagicMock()
sys.modules["app.services.global_state"] = MagicMock()
sys.modules["app.adapters.market"] = MagicMock()
sys.modules["app.adapters.llm"] = MagicMock()
sys.modules["app.adapters.sentiment"] = MagicMock()
sys.modules["app.adapters.chronos"] = MagicMock()
sys.modules["app.lib.kalman"] = MagicMock()
sys.modules["app.lib.physics.heavy_tail"] = MagicMock()

# Import logic under test
from app.agent.nodes.analyst import AnalystAgent
from app.agent.state import AgentState, OrderSide
from app.lib.memory import FractalMemory  # We will mock the method of this class

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DynamicStrategyTest")


def test_dynamic_strategy():
    agent = AnalystAgent()

    # Mock specific dependencies for the test
    agent.market.get_current_price.return_value = 100.0
    agent.market.get_historic_returns.return_value = [0.01] * 30  # Dummy returns
    agent.llm.get_trade_signal.return_value = {
        "signal_side": "BUY",
        "signal_confidence": 0.8,
        "reasoning": "Mock LLM Response",
    }

    # Mock Physics
    agent.kf.update.return_value = MagicMock(velocity=0.5, acceleration=0.1)

    # Mock Chronos to prevent TypeError
    agent.chronos.predict.return_value = {
        "median": [101.0],  # Float > current_price (100.0)
        "low": [99.0],
        "high": [103.0],
    }

    # Case 1: TREND Mode (Hurst = 0.6)
    logger.info("🧪 TEST 1: TREND Mode (Hurst=0.6)...")
    FractalMemory.calculate_hurst = MagicMock(return_value=0.6)
    FractalMemory.frac_diff = MagicMock(return_value=[1.0] * 30)

    state_trend = AgentState(
        symbol="SPY",
        messages=[],
        price=100.0,
        historic_returns=[],
        current_alpha=0.0,
        regime="Gaussian",
        hurst=0.0,
        strategy_mode="",
        chronos_forecast={},
        signal_side="",
        signal_confidence=0.0,
        reasoning="",
        approved_size=0.0,
        risk_multiplier=0.0,
        nav=100000.0,
        cash=100000.0,
        daily_pnl=0.0,
        max_drawdown=0.0,
        status="ACTIVE",
    )

    res_trend = agent.analyze(state_trend)

    if res_trend["strategy_mode"] == "TREND":
        logger.info("✅ PASS: Mode is TREND.")
    else:
        logger.error(f"❌ FAIL: Expected TREND, got {res_trend.get('strategy_mode')}")

    if res_trend["signal_side"] == "BUY":  # Should proceed to LLM
        logger.info("✅ PASS: Signal generated (LLM invoked).")
    else:
        logger.error(
            f"❌ FAIL: Expected BUY signal, got {res_trend.get('signal_side')}"
        )

    # Case 2: MEAN_REVERSION Mode (Hurst = 0.4)
    logger.info("\n🧪 TEST 2: MEAN_REVERSION Mode (Hurst=0.4)...")
    FractalMemory.calculate_hurst = MagicMock(return_value=0.4)

    res_mr = agent.analyze(state_trend.copy())  # Reuse clean state

    if res_mr["strategy_mode"] == "MEAN_REVERSION":
        logger.info("✅ PASS: Mode is MEAN_REVERSION.")
    else:
        logger.error(
            f"❌ FAIL: Expected MEAN_REVERSION, got {res_mr.get('strategy_mode')}"
        )

    # Case 3: NOISE Mode (Hurst = 0.5) - HARD STOP
    logger.info("\n🧪 TEST 3: NOISE Mode (Hurst=0.5)...")
    FractalMemory.calculate_hurst = MagicMock(return_value=0.5)

    res_noise = agent.analyze(state_trend.copy())

    if res_noise["strategy_mode"] == "NOISE":
        logger.info("✅ PASS: Mode is NOISE.")
    else:
        logger.error(f"❌ FAIL: Expected NOISE, got {res_noise.get('strategy_mode')}")

    if res_noise["signal_side"] == "FLAT" and res_noise["signal_confidence"] == 1.0:
        logger.info("✅ PASS: Signal forced to FLAT with 1.0 confidence (LLM Skipped).")
    else:
        logger.error(
            f"❌ FAIL: Noise did not force FLAT. Signal: {res_noise.get('signal_side')}"
        )


if __name__ == "__main__":
    test_dynamic_strategy()
