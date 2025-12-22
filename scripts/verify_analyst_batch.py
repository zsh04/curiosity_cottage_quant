import asyncio
import logging
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path (Force local import)
sys.path.insert(0, os.getcwd())

from app.agent.boyd import boyd_node
from app.agent.state import AgentState, TradingStatus

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_ANALYST")


# Mock AgentState
def create_mock_state():
    return {
        "status": TradingStatus.ACTIVE,
        "symbol": "DEFAULT",
        "watchlist": [
            {"symbol": "TSLA", "signal_potential": 0.4},
            {"symbol": "AAPL", "signal_potential": 0.1},
            {"symbol": "NVDA", "signal_potential": 0.3},
        ],
        "candidates": [],  # Old key, should be ignored/updated
        "history": [],
        "messages": [],
    }  # type: ignore


# Mock dependencies
@patch("app.agent.boyd.MarketService")
@patch("app.agent.boyd.FeynmanBridge")
@patch("app.agent.boyd.TimeSeriesForecaster")
@patch("app.agent.boyd.ReasoningService")
async def test_analyst_batch(MockReasoning, MockForecast, MockPhysics, MockMarket):
    print("🚀 Starting Analyst Batch Verification...")

    # Setup Mocks
    market_mock = MockMarket.return_value
    market_mock.get_market_snapshot.side_effect = lambda sym: {
        "symbol": sym,
        "price": 100.0,
        "history": [100.0] * 20,
        "sentiment": {},
    }
    market_mock.get_startup_bars.return_value = [100.0] * 100

    physics_mock = MockPhysics.return_value
    physics_mock.is_initialized = True
    physics_mock.calculate_kinematics.return_value = {
        "velocity": 1.0,
        "acceleration": 0.1,
    }
    physics_mock.analyze_regime.return_value = {"regime": "Gaussian", "alpha": 2.5}
    physics_mock.calculate_hurst_and_mode.return_value = {
        "hurst": 0.6,
        "strategy_mode": "Trend",
    }
    physics_mock.calculate_qho_levels.return_value = {}

    # Reasoning Mock with varying confidence to test sorting
    def mock_reasoning(ctx):
        sym = ctx["market"]["symbol"]
        conf = 0.5
        if sym == "TSLA":
            conf = 0.9
        if sym == "AAPL":
            conf = 0.1
        if sym == "NVDA":
            conf = 0.7
        return {
            "signal_side": "BUY",
            "signal_confidence": conf,
            "reasoning": f"Simulated analysis for {sym}",
        }

    MockReasoning.return_value.generate_signal.side_effect = mock_reasoning

    # Run
    state = create_mock_state()
    result_state = await boyd_node(state)

    # Checks
    print("\n📊 Verification Results:")

    # 1. Check Superposition Output
    reports = result_state.get("analysis_reports", [])
    print(f"📦 Analysis Reports Count: {len(reports)}")
    if len(reports) == 3:
        print("✅ Correct number of analysis reports generated.")
    else:
        print(f"❌ Expected 3 reports, got {len(reports)}")

    # 2. Check Parallel Mapping
    symbols_processed = [r["symbol"] for r in reports]
    print(f"🔍 Symbols Processed: {symbols_processed}")
    if set(symbols_processed) == {"TSLA", "AAPL", "NVDA"}:
        print("✅ All watchlist symbols processed.")
    else:
        print("❌ Missing symbols in processing.")

    # 3. Check Collapse (Winner Selection)
    winner = result_state.get("symbol")
    conf = result_state.get("signal_confidence")
    print(f"🏆 Selected Winner: {winner} (Conf: {conf})")

    # Expect TSLA because we mocked it with 0.9 confidence
    if winner == "TSLA" and conf == 0.9:
        print("✅ Winner selected correctly based on confidence.")
    else:
        print(f"❌ Winner selection logic failed. Expected TSLA, got {winner}")

    # 4. Check State Population
    if "velocity" in result_state and "regime" in result_state:
        print("✅ Top-level state populated with Winner details.")
    else:
        print("❌ Top-level state missing physical details.")


if __name__ == "__main__":
    asyncio.run(test_analyst_batch())
