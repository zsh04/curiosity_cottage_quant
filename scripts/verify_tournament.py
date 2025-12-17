import logging
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.getcwd())

from app.agent.nodes.risk import risk_node
from app.agent.state import AgentState, TradingStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_TOURNAMENT")


def create_mock_state():
    return {
        "status": TradingStatus.ACTIVE,
        "symbol": "OLD_SYM",
        "signal_side": "BUY",
        "analysis_reports": [
            {
                "symbol": "BAD_PHYSICS",
                "signal_side": "BUY",
                "signal_confidence": 0.9,
                "current_alpha": 1.5,  # Should be risky
                "regime": "Critical",
                "price": 100.0,
                "reasoning": "High return but dangerous.",
            },
            {
                "symbol": "GOOD_PHYSICS",
                "signal_side": "BUY",
                "signal_confidence": 0.8,
                "current_alpha": 2.5,  # Safe
                "regime": "Gaussian",
                "price": 200.0,
                "reasoning": "Solid trend, safe physics.",
            },
        ],
        "nav": 100000.0,
        "current_positions": [],
        "chronos_forecast": {
            "expected_price": 210.0,
            "lower_bound": 190.0,
        },  # Needed for sizing
    }


@patch("app.agent.nodes.risk.RiskManager")
@patch("app.services.reasoning.ReasoningService")
@patch(
    "app.services.market.MarketService"
)  # Mock market to avoid entanglement check errors
def test_tournament(MockMarket, MockReasoning, MockRiskManager):
    print("🚀 Starting AI Tournament Verification...")

    # Mock Reasoning Service to simulate LLM picking the SAFE candidate
    reasoning_instance = MockReasoning.return_value
    reasoning_instance.arbitrate_tournament.return_value = {
        "winner_symbol": "GOOD_PHYSICS",
        "rationale": "Selected GOOD_PHYSICS because BAD_PHYSICS has critical regime.",
    }

    # Mock Risk Logic (Pass-through for check_governance, real-ish for sizing)
    risk_instance = MockRiskManager.return_value
    risk_instance.check_governance.side_effect = lambda s: s  # No governance halt
    risk_instance.size_position.return_value = 5000.0  # Return some size
    risk_instance.bes.estimate_es.return_value = 0.05  # Return float for logging

    # Run
    state = create_mock_state()
    result = risk_node(state)

    print("\n📊 Verification Results:")

    # 1. Did it pick the winner?
    winner = result.get("symbol")
    print(f"🏆 Final Symbol in State: {winner}")

    if winner == "GOOD_PHYSICS":
        print("✅ Tournament correctly overwrote the state with Winner.")
    else:
        print(f"❌ Tournament Failed. Expected GOOD_PHYSICS, got {winner}")

    # 2. Did rationale update?
    reason = result.get("reasoning", "")
    print(f"📝 Final Reasoning: {reason}")
    if "[TOURNAMENT WINNER]" in reason:
        print("✅ Logic Confirmation present in reasoning.")
    else:
        print("❌ Reasoning tag missing.")


if __name__ == "__main__":
    test_tournament()
