import time
import logging
from unittest.mock import MagicMock, patch
import sys
import os
import random

# Add project root to path (Force local import)
sys.path.insert(0, os.getcwd())

from app.agent.nodes.macro import macro_node
from app.agent.state import AgentState, TradingStatus

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_MACRO")


def mock_get_snapshot(symbol):
    """
    Simulate network latency and return dummy data.
    """
    time.sleep(0.1)  # 100ms latency

    price = random.uniform(50.0, 500.0)
    open_p = price * random.uniform(0.95, 1.05)
    vol = random.randint(500_000, 5_000_000)

    # Specific Cases for testing filter
    if symbol == "TRASH":
        price = 5.0
        vol = 100
    if symbol == "WINNER":
        price = 100.0
        open_p = 90.0  # +11%
        vol = 10_000_000  # High Energy

    return {
        "symbol": symbol,
        "price": price,
        "open": open_p,
        "volume": vol,
        "history": [],
        "news": [],
        "sentiment": {"label": "neutral", "score": 0.5},
    }


def verify_parallel_macro():
    print("🚀 Starting Parallel Macro Node Verification...")

    # Mock MarketService
    with patch("app.agent.nodes.macro.MarketService") as MockService:
        instance = MockService.return_value
        instance.get_market_snapshot.side_effect = mock_get_snapshot

        # Inject "WINNER" and "TRASH" into UNIVERSE for the test
        # We need to patch the UNIVERSE constant in the module
        with patch(
            "app.agent.nodes.macro.UNIVERSE",
            ["SPY", "QQQ", "WINNER", "TRASH", "AAPL", "MSFT", "TSLA", "NVDA"],
        ):
            # Create Dummy State
            state: AgentState = {
                "status": TradingStatus.ACTIVE,
                "messages": [],
                "candidates": [],
            }  # type: ignore

            start_t = time.time()
            result = macro_node(state)
            end_t = time.time()

            duration = end_t - start_t

            # Checks
            print(f"⏱️ Execution Time: {duration:.4f}s")

            # 8 symbols * 0.1s latency = 0.8s if sequential.
            # Should be ~0.1s + overhead if parallel.
            if duration < 0.3:
                print("✅ Parallel Execution Confirmed (Duration < 0.3s)")
            else:
                print("❌ Parallel Execution FAILED (Too Slow)")

            # Check Winner (Top of Watchlist)
            winner = result.get("symbol")
            watchlist = result.get("watchlist", [])

            print(f"🏆 Winner: {winner}")
            print(f"📋 Watchlist Size: {len(watchlist)}")

            if winner == "WINNER":
                print("✅ Winner Selection Logic Confirmed")
            elif winner:
                print(
                    f"⚠️ Winner is {winner} (Expected WINNER, but randomness might affect mocks)"
                )

            if len(watchlist) > 0:
                top = watchlist[0]
                print(
                    f"🥇 Top Candidate: {top['symbol']} | Score: {top.get('signal_potential', 0):.4f}"
                )

                if "hurst" in top:
                    print(f"✅ Hurst Calculated: {top['hurst']:.4f}")
                else:
                    print("❌ Hurst Metric Missing")

                if "signal_potential" in top:
                    print("✅ Signal Potential Calculated")
                else:
                    print("❌ Signal Potential Missing")
            else:
                print("❌ Watchlist Empty")


if __name__ == "__main__":
    verify_parallel_macro()
