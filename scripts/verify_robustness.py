import asyncio
import time
import logging
from unittest.mock import patch, MagicMock
import sys
import os
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.getcwd())

from app.agent.nodes.analyst import analyst_node, AnalystAgent
from app.agent.state import AgentState, TradingStatus
from app.lib.physics import Regime

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_ROBUSTNESS")

# Bypass Alpaca Auth for Tests
os.environ["ALPACA_API_KEY"] = "pk_dummy"
os.environ["ALPACA_API_SECRET"] = "sk_dummy"


def verify_robustness():
    print("🚀 Starting Quantum Robustness Verification (Resilient Collapse)...")

    # Scenario:
    # Candidate 0: "CRASH_CO" (Conf 0.99, Alpha 1.5 - CRITICAL) -> MUST VETO
    # Candidate 1: "STABLE_INC" (Conf 0.90, Alpha 2.5 - STABLE) -> MUST WIN
    # Candidate 2: "DUD_CORP" (Conf 0.50, Alpha 3.0) -> IGNORED

    candidates = [
        {"symbol": "CRASH_CO"},
        {"symbol": "STABLE_INC"},
        {"symbol": "DUD_CORP"},
    ]

    state = {
        "status": TradingStatus.ACTIVE,
        "messages": [],
        "candidates": candidates,
        "cash": 100000.0,
    }

    # Mock Services
    with (
        patch("app.agent.nodes.analyst.MarketService") as MockMarket,
        patch("app.agent.nodes.analyst.PhysicsService") as MockPhysics,
        patch("app.agent.nodes.analyst.ForecastingService") as MockForecast,
        patch("app.agent.nodes.analyst.ReasoningService") as MockReason,
        patch("app.agent.nodes.analyst.MemoryService") as MockMemory,
    ):
        # 1. Market Mock
        def mock_get_snapshot(symbol):
            return {
                "symbol": symbol,
                "price": 100.0,
                "history": [10.0] * 50,
                "sentiment": {"label": "neutral", "score": 0.5},
            }

        MockMarket.return_value.get_market_snapshot.side_effect = mock_get_snapshot

        # 2. Physics Mock (The Critical Part)
        # We need _analyze_single to return the correct Regime/Alpha for each symbol
        # But _analyze_single calls PhysicsService.analyze_regime

        def mock_analyze_regime(history):
            # We can't see 'symbol' here easily in the real flow (it passes history list)
            # BUT, we can make the mock stateful or side_effect based on history content? No.
            # Trick: Analyst _analyze_single fetches snapshot first.
            # We can rely on the Order of execution since it's asyncio.gather.
            # Wait, asyncio.gather is concurrent, order is not guaranteed.
            # We need a better way to link Symbol -> Regime in mocks.
            # Since we mock the *method* on the *instance*, and we use `asyncio.to_thread`.
            # We can use side_effect with a checker, but arguments are just `history`.

            # Alternative: Mock `_analyze_single` directly? No, we want to test the selection loop logic
            # which happens AFTER _analyze_single results are merged.
            # The Selection Loop uses result keys `current_alpha` and `regime`.
            # So if we can control what `_analyze_single` returns via `Regime` service, we are good.
            # But the service doesn't know the symbol.

            # Solution: We Mock `_analyze_single` instead of the sub-services for THIS test?
            # It's an architectural unit test of the Selection Logic.
            # Yes, that's cleaner for testing the "Collapse" logic.
            return {"regime": "Gaussian", "alpha": 3.0}  # Default

        # ACTUALLY: Let's Mock `AnalystAgent._analyze_single` directly on the class/instance
        # This bypasses the complexity of mocking sub-services to produce specific data per symbol
        pass

    # We need to patch the METHOD method on the class for the test duration
    original_analyze_single = AnalystAgent._analyze_single

    async def mock_analyze_single(self, symbol: str) -> Dict[str, Any]:
        result = {
            "symbol": symbol,
            "price": 100.0,
            "history": [],
            "success": True,
            # Default
            "velocity": 0,
            "acceleration": 0,
            "hurst": 0.5,
            "strategy_mode": "N",
        }

        if symbol == "CRASH_CO":
            result.update(
                {
                    "signal_side": "BUY",
                    "signal_confidence": 0.99,
                    "regime": Regime.CRITICAL.value,
                    "current_alpha": 1.5,  # FAIL
                    "reasoning": "High confidence but CRITICAL regime.",
                }
            )
        elif symbol == "STABLE_INC":
            result.update(
                {
                    "signal_side": "BUY",
                    "signal_confidence": 0.90,
                    "regime": Regime.LEVY_STABLE.value,  # Correct Enum
                    "current_alpha": 2.5,  # PASS
                    "reasoning": "Good confidence, Stable regime.",
                }
            )
        elif symbol == "DUD_CORP":
            result.update(
                {
                    "signal_side": "FLAT",
                    "signal_confidence": 0.50,
                    "regime": "Gaussian",
                    "current_alpha": 3.0,
                    "reasoning": "Boring.",
                }
            )

        # Sleep to simulate async
        await asyncio.sleep(0.01)
        return result

    # Apply Patch
    with patch.object(
        AnalystAgent, "_analyze_single", side_effect=mock_analyze_single, autospec=True
    ):
        print("🧪 Testing Analyst Node with mocked results...")
        start_t = time.time()
        result_state = analyst_node(state)
        end_t = time.time()

        print(f"⏱️ Execution Time: {end_t - start_t:.4f}s")
        winner = result_state["symbol"]
        conf = result_state["signal_confidence"]
        regime = result_state["regime"]

        print(f"🏆 Winner: {winner}")
        print(
            f"📊 Stats: Conf={conf:.2f} | Regime={regime} | Alpha={result_state.get('current_alpha')}"
        )

        # ASSERTIONS
        if winner == "STABLE_INC":
            print("✅ SUCCESS: Resilient Collapse worked! 'CRASH_CO' was vetoed.")
        elif winner == "CRASH_CO":
            print(
                "❌ FAILURE: 'CRASH_CO' was selected despite Critical Regime. Vulnerability exists!"
            )
        else:
            print(f"❌ FAILURE: Unexpected winner {winner}")


if __name__ == "__main__":
    verify_robustness()
