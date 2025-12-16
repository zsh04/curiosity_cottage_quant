"""
Execution Agent Node.
Responsible for executing trades based on Risk-approved sizing.
"""

import time
import logging
from typing import Optional
from app.agent.state import AgentState, TradingStatus
from app.services.global_state import get_global_state_service, get_current_snapshot_id

logger = logging.getLogger(__name__)


class ExecutionAgent:
    """
    Manages order lifecycle, executing trades that have passed the Iron Gate (Risk).
    """

    def __init__(self):
        pass

    def execute(self, state: AgentState) -> AgentState:
        """
        Executes the trade if validated and approved.
        """
        start_time = time.time()
        success = True
        error_msg = None
        trade_executed = False

        try:
            # 1. Inputs
            approved_size = state.get("approved_size", 0.0)
            signal_side = state.get("signal_side")
            price = state.get("price", 0.0)
            symbol = state.get("symbol")
            status = state.get("status")

            # 2. Validation Guard
            if approved_size <= 0:
                print("EXECUTION: Idle")
                return state

            if status != TradingStatus.ACTIVE:
                print("EXECUTION: BLOCKED")
                return state

            if price <= 0:
                print(f"EXECUTION: Error - Invalid Price {price}")
                return state

            # 3. Simulation Logic (Phase 1)
            qty = approved_size / price

            # Update simulation cash
            current_cash = state.get("cash", 0.0)
            state["cash"] = current_cash - approved_size

            # Log confirmation
            trade_executed = True
            log_msg = (
                f"EXECUTION: ⚡ SENT ORDER: {signal_side} {symbol} | "
                f"Amt: ${approved_size:.2f} | Qty: {qty:.4f} | Price: ${price:.2f}"
            )
            print(log_msg)

            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(log_msg)

        except Exception as e:
            success = False
            error_msg = f"EXECUTION: 💥 CRASH: {e}"
            print(error_msg)
            logger.exception(error_msg)
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(error_msg)

        finally:
            # TRACK EXECUTION PERFORMANCE
            latency = (time.time() - start_time) * 1000
            state_service = get_global_state_service()
            snapshot_id = get_current_snapshot_id()
            if state_service and snapshot_id:
                state_service.save_agent_metrics(
                    snapshot_id=snapshot_id,
                    agent_name="execution",
                    latency_ms=latency,
                    success=success,
                    output_data={
                        "trade_executed": trade_executed,
                        "approved_size": state.get("approved_size"),
                        "signal_side": state.get("signal_side"),
                        "cash_remaining": state.get("cash"),
                    },
                    error=error_msg,
                )

        return state


def execution_node(state: AgentState) -> AgentState:
    """
    LangGraph node for execution.
    """
    agent = ExecutionAgent()
    return agent.execute(state)
