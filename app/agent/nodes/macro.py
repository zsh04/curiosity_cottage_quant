"""
Macro Agent Node.
"""

from typing import Dict, Any
from app.agent.state import AgentState, TradingStatus


class MacroAgent:
    """
    Monitors global liquidity and sets the Regime State.
    Has VETO power: Can force status to SLEEPING if macro conditions are toxic.
    """

    def check_macro_environment(self, state: AgentState) -> AgentState:
        # Stub: Monitor Bond Yield Spreads or VIX
        # For prototype, we assume benign environment unless specifically simulated

        # Example Logic:
        # yield_spread = monitor_yield_curve()
        # if yield_spread < 0 (Inverted):
        #    state["messages"].append("MACRO: Yield Curve Inverted. Defensive Mode.")
        #    ...

        # Pass-through for now
        state["messages"].append(
            {"role": "system", "content": "MACRO: Environment Neutral. Proceeding."}
        )
        return state


def macro_node(state: AgentState) -> AgentState:
    agent = MacroAgent()
    return agent.check_macro_environment(state)
