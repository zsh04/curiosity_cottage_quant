import asyncio
import time
import logging
from unittest.mock import patch
import sys
import os
import random

# Add project root to path
sys.path.insert(0, os.getcwd())

from app.agent.nodes.analyst import analyst_node, AnalystAgent
from app.agent.state import AgentState, TradingStatus

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_ANALYST")


async def mock_to_thread(func, *args, **kwargs):
    """
    Simulate work and IO latency.
    """
    # Simulate API call latency + Processing
    await asyncio.sleep(0.1)

    # Map function to mock return
    func_name = getattr(func, "__name__", str(func))

    if "get_market_snapshot" in func_name:
        symbol = args[0]
        return {
            "symbol": symbol,
            "price": 100.0,
            "history": [100.0] * 50,
            "sentiment": {"label": "neutral", "score": 0.5},
        }
    if "calculate_kinematics" in func_name:
        return {"velocity": 0.1, "acceleration": 0.05}
    if "analyze_regime" in func_name:
        return {"regime": "Gaussian", "alpha": 2.1}
    if "calculate_hurst_and_mode" in func_name:
        return {"hurst": 0.55, "strategy_mode": "MeanReversion"}
    if "predict_trend" in func_name:
        return {"trend": "up", "forecast_array": []}
    if "retrieve_similar" in func_name:
        return []

    if "generate_signal" in func_name:
        # Determine confidence based on context symbol (trick)
        # We need a way to make one symbol the winner.
        # But this mock is generic.
        # Let's rely on random or patched logic?
        # Actually logic is inside ReasoningService.
        # We'll just return a random-ish confidence to test sorting.
        return {
            "signal_side": "BUY",
            "signal_confidence": random.uniform(0.1, 0.9),
            "reasoning": "Mock Reasoning",
        }

    return {}


def verify_batch():
    print("🚀 Starting Analyst Batch Verification...")

    candidates = [
        {"symbol": "ALPHA"},
        {"symbol": "BETA"},
        {"symbol": "GAMMA", "signal_confidence": 0.99},
        {"symbol": "DELTA"},
        {"symbol": "EPSILON"},
    ]

    state = {
        "status": TradingStatus.ACTIVE,
        "messages": [],
        "candidates": candidates,
    }

    # Mock Services
    with (
        patch("app.agent.nodes.analyst.MarketService") as MockMarket,
        patch("app.agent.nodes.analyst.PhysicsService") as MockPhysics,
        patch("app.agent.nodes.analyst.ForecastingService") as MockForecast,
        patch("app.agent.nodes.analyst.ReasoningService") as MockReason,
        patch("app.agent.nodes.analyst.MemoryService") as MockMemory,
    ):
        # Configure Market Mock to return correct symbol
        def mock_get_snapshot(symbol):
            return {
                "symbol": symbol,
                "price": 100.0,
                "history": [10.0] * 10,
                "sentiment": {"label": "neutral", "score": 0.5},
            }

        MockMarket.return_value.get_market_snapshot.side_effect = mock_get_snapshot

        # Configure Physics/Forecast to return valid dicts avoiding attribute errors
        MockPhysics.return_value.calculate_kinematics.return_value = {
            "velocity": 0,
            "acceleration": 0,
        }
        MockPhysics.return_value.analyze_regime.return_value = {
            "regime": "Gaussian",
            "alpha": 2.0,
        }
        MockPhysics.return_value.calculate_hurst_and_mode.return_value = {
            "hurst": 0.5,
            "strategy_mode": "MR",
        }
        MockForecast.return_value.predict_trend.return_value = {}
        MockMemory.return_value.retrieve_similar.return_value = []

        # Mock generate_signal to return High Confidence for GAMMA
        def side_effect_reasoning(context):
            sym = context["market"]["symbol"]
            conf = 0.5
            if sym == "GAMMA":
                conf = 0.95
            if sym == "ALPHA":
                conf = 0.1
            return {
                "signal_side": "BUY",
                "signal_confidence": conf,
                "reasoning": f"Analysis for {sym}",
            }

        MockReason.return_value.generate_signal.side_effect = side_effect_reasoning

        # Start Timer
        start_t = time.time()
        result_state = analyst_node(state)
        end_t = time.time()

        duration = end_t - start_t
        print(f"⏱️ Batch Execution Time: {duration:.4f}s")

        print(f"🏆 Selected Symbol: {result_state['symbol']}")
        print(f"Conf: {result_state['signal_confidence']}")

        if (
            result_state["symbol"] == "GAMMA"
            and result_state["signal_confidence"] == 0.95
        ):
            print("✅ Selection Logic Confirmed (Picked GAMMA)")
        else:
            print(f"❌ Selection Failed. Got {result_state['symbol']}")

        print(f"📦 Output Candidates Enriched: {len(result_state['candidates'])}")
        if "signal_side" in result_state["candidates"][0]:
            print("✅ Candidates Enriched")


if __name__ == "__main__":
    verify_batch()
