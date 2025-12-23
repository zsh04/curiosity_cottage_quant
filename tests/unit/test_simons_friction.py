# import pytest
from app.agent.nodes.simons import simons_node
from app.agent.state import AgentState, TradingStatus

# Mock Logger
import logging

logger = logging.getLogger("app.agent.nodes.simons")
logger.setLevel(logging.INFO)


def test_simons_min_notional():
    """
    Verify that Simons rejects trades with Notional Value < $5.00.
    """

    # CASE 1: Dust Trade (Value $4.00) -> REJECT
    state_dust: AgentState = {
        "signal_side": "BUY",
        "symbol": "PENNY",
        "status": "active",
        "approved_size": 4.00,  # $4 Allocation
        "price": 1.00,
        "cash": 1000.0,
        "buying_power": 1000.0,
        "messages": [],
    }

    result_dust = simons_node(state_dust)

    # Check that NO trade was executed (no log in messages confirming trade?)
    # Since verified execution puts a log in messages or changes cash (in simulation).
    # In live/simons node, if it returns early, 'messages' should imply skip or lack of "SENT ORDER".

    # The current simons node log warning isn't appended to messages list in the code I wrote?
    # Wait, let's check simons.py again. It logs to logger.warning.
    # It returns state.
    # It does NOT update cash if it returns early.

    assert result_dust["cash"] == 1000.0  # Unchanged
    # "SENT ORDER" should not be in logs/messages if we capture them.
    # But since I can't easily capture logger output in this simple script without caplog,
    # I rely on cash not changing.

    print("\n✅ CASE 1 Passed: Dust Trade ($4.00) Skipped (Cash Unchanged).")

    # CASE 2: Valid Trade (Value $10.00) -> EXECUTE
    state_valid: AgentState = {
        "signal_side": "BUY",
        "symbol": "SOLID",
        "status": TradingStatus.ACTIVE,
        "approved_size": 10.00,
        "price": 1.00,
        "cash": 1000.0,
        "buying_power": 1000.0,
        "messages": [],
    }

    result_valid = simons_node(state_valid)

    # Cash should decrease (Simulated Execution logic in the node for backtest/dry-run?)
    # Wait, does execution_node modify cash?
    # Looking at the code: "state['cash'] -= approved_size" inside the block.

    assert result_valid["cash"] == 1000.0 - 10.0
    print("✅ CASE 2 Passed: Valid Trade ($10.00) Executed.")


if __name__ == "__main__":
    test_simons_min_notional()
