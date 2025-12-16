"""
Execution Agent Node.
Responsible for executing trades based on Risk-approved sizing.
"""

from app.agent.state import AgentState, TradingStatus


class ExecutionAgent:
    """
    Manages order lifecycle, executing trades that have passed the Iron Gate (Risk).
    """

    def execute(self, state: AgentState) -> AgentState:
        """
        Executes the trade if validated and approved.
        """
        # 1. Inputs
        approved_size = state.get("approved_size", 0.0)
        signal_side = state.get("signal_side")
        price = state.get("price", 0.0)
        symbol = state.get("symbol")
        status = state.get("status")

        # 2. Validation Guard
        # If no size approved, we are idle.
        if approved_size <= 0:
            print("EXECUTION: Idle")
            return state

        # If system is not ACTIVE (e.g. Halted), we are blocked.
        if status != TradingStatus.ACTIVE:
            print("EXECUTION: BLOCKED")
            return state

        # Safety check for price to avoid division by zero
        if price <= 0:
            print(f"EXECUTION: Error - Invalid Price {price}")
            return state

        # 3. Simulation Logic (Phase 1)
        # Calculate quantity
        qty = approved_size / price

        # Update simulation cash (simple model: deduct full notional)
        # In a full engine, this would depend on side (Buy consumes cash, Sell adds cash/margin),
        # but requirements specify: "Update state['cash'] by subtracting approved_size".
        # We will follow this strictly for Phase 1.
        current_cash = state.get("cash", 0.0)
        state["cash"] = current_cash - approved_size

        # Log confirmation
        log_msg = (
            f"EXECUTION: ⚡ SENT ORDER: {signal_side} {symbol} | "
            f"Amt: ${approved_size:.2f} | Qty: {qty:.4f} | Price: ${price:.2f}"
        )
        print(log_msg)

        # Optionally append to state messages if desired, but requirements just said "Log".
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append(log_msg)

        return state


def execution_node(state: AgentState) -> AgentState:
    """
    LangGraph node for execution.
    """
    agent = ExecutionAgent()
    return agent.execute(state)
