"""
Execution Agent Node.
"""

from app.agent.state import AgentState


class ExecutionAgent:
    """
    Manages order lifecycle.
    """

    def execute_order(self, state: AgentState) -> AgentState:
        # This node runs AFTER Risk Manager has calculated 'final_size' (if we added that to state)
        # OR, Risk Manager sets the constraints and Execution calculates final parameters.

        # For this v0.1, Risk calculates size.
        # But 'final_size' isn't explicitly in TypedDict yet.
        # We'll assume the Risk Manager might have updated 'messages' or we need to add a field.

        state["messages"].append(
            {
                "role": "system",
                "content": "EXECUTION: Received control. Simulation Mode - No Order Sent.",
            }
        )
        return state


def execution_node(state: AgentState) -> AgentState:
    agent = ExecutionAgent()
    return agent.execute_order(state)
