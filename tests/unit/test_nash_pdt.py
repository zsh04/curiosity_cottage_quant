# import pytest
from app.agent.nash import NashAgent
from app.agent.state import AgentState

# Mock Logger
import logging

logger = logging.getLogger("app.agent.nash")
logger.setLevel(logging.INFO)


def test_nash_pdt_exemption():
    """
    Verify that Nash allows trades with Low BP if the account is PDT Exempt (> $25k).
    """
    agent = NashAgent()

    # CASE 1: Micro-Account (Non-Exempt), Low BP -> VETO
    state_micro: AgentState = {
        "signal_side": "BUY",
        "symbol": "SPY",
        "buying_power": 5.0,  # Below $20 Threshold
        "pdt_exempt": False,
        "reasoning": "",
        "candidates": [],
    }

    result_micro = agent.audit(state_micro)
    # Should be flattened
    assert result_micro["signal_side"] == "FLAT"
    assert "Settlement Lock" in result_micro["reasoning"]
    print("\n✅ CASE 1 Passed: Micro-Account Low BP correctly Vetoed.")

    # CASE 2: Whale Account (Exempt), Low BP -> ALLOWED
    # (e.g., heavily invested but still has margin or just noise)
    # Actually, if BP is low, they can't buy anyway, but Nash shouldn't block purely on "Settlement Risk"
    # if they are margin. But wait, if BP < 20, they physically can't buy much.
    # However, the logic we added is: if NOT exempt AND BP < threshold.
    # So if Exempt, we skip the block.

    state_whale: AgentState = {
        "signal_side": "BUY",
        "symbol": "SPY",
        "buying_power": 5.0,  # Below $20 Threshold
        "pdt_exempt": True,  # RICH
        "reasoning": "",
        "candidates": [],
    }

    result_whale = agent.audit(state_whale)
    # Should NOT be flattened by Settlement Lock (might be by Nash Dist, but Dist is 0 here)
    assert result_whale["signal_side"] == "BUY"
    assert "Settlement Lock" not in result_whale["reasoning"]
    print("✅ CASE 2 Passed: PDT Exempt Account ignored Settlement Lock.")

    # CASE 3: Micro-Account, High BP -> ALLOWED
    state_funded: AgentState = {
        "signal_side": "BUY",
        "symbol": "SPY",
        "buying_power": 1000.0,
        "pdt_exempt": False,
        "reasoning": "",
        "candidates": [],
    }
    result_funded = agent.audit(state_funded)
    assert result_funded["signal_side"] == "BUY"
    print("✅ CASE 3 Passed: Micro-Account with Cash allowed.")


if __name__ == "__main__":
    test_nash_pdt_exemption()
