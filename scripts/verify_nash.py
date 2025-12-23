import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

from app.agent.nash import NashAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TEST_NASH")


def test_nash_veto():
    agent = NashAgent()

    # Case 1: BUY Signal with High Nash (Overextended Top) -> VETO
    state_buy_high = {
        "symbol": "BTC/USD",
        "signal_side": "BUY",
        "reasoning": "Momentum is strong",
        "candidates": [
            {
                "symbol": "BTC/USD",
                "physics_vector": {"nash_dist": 2.5},  # Too high
            }
        ],
    }

    result = agent.audit(state_buy_high)
    logger.info(f"Case 1 (Buy High): Signal={result['signal_side']}")
    assert result["signal_side"] == "FLAT"
    assert "NASH VETO" in result["reasoning"]

    # Case 2: SELL Signal with Low Nash (Overextended Bottom) -> VETO
    state_sell_low = {
        "symbol": "BTC/USD",
        "signal_side": "SELL",
        "reasoning": "Momentum is weak",
        "candidates": [
            {
                "symbol": "BTC/USD",
                "physics_vector": {"nash_dist": -2.5},  # Too low
            }
        ],
    }

    result = agent.audit(state_sell_low)
    logger.info(f"Case 2 (Sell Low): Signal={result['signal_side']}")
    assert result["signal_side"] == "FLAT"
    assert "NASH VETO" in result["reasoning"]

    # Case 3: BUY Signal with Normal Nash -> PASS
    state_buy_normal = {
        "symbol": "BTC/USD",
        "signal_side": "BUY",
        "reasoning": "Momentum is strong",
        "candidates": [{"symbol": "BTC/USD", "physics_vector": {"nash_dist": 1.0}}],
    }

    result = agent.audit(state_buy_normal)
    logger.info(f"Case 3 (Buy Normal): Signal={result['signal_side']}")
    assert result["signal_side"] == "BUY"
    assert "NASH VETO" not in result["reasoning"]

    print("✅ Nash Verification PASSED")


if __name__ == "__main__":
    try:
        test_nash_veto()
    except Exception as e:
        logger.error(f"❌ Nash Verification FAILED: {e}")
        sys.exit(1)
