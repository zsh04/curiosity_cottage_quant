from typing import Literal

from langgraph.graph import StateGraph, START, END
from app.agent.state import AgentState, TradingStatus
from app.agent.nodes.risk import risk_node
from app.agent.nodes.macro import macro_node
from app.agent.nodes.analyst import analyst_node
from app.agent.nodes.execution import execution_node

# Define the graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("macro_context", macro_node)
builder.add_node("analyst_engine", analyst_node)
builder.add_node("risk_guardian", risk_node)
builder.add_node("execution_engine", execution_node)

# Define edges
# 1. Start -> Macro (Check Global Liquidity)
builder.add_edge(START, "macro_context")

# 2. Macro -> Analyst (If Macro Veto doesn't sleep)
# Needing conditional edge here if Macro has Veto power?
# For now, simplistic: Macro -> Analyst
builder.add_edge("macro_context", "analyst_engine")

# 3. Analyst -> Risk (Submit Signal for Governance)
builder.add_edge("analyst_engine", "risk_guardian")


# 4. Risk -> Execution (Conditional on Governance)
def route_after_risk(state: AgentState) -> Literal[END, "execution_engine"]:
    """
    Decide next step based on Risk Governance.
    """
    if state["status"] in [
        TradingStatus.HALTED_PHYSICS,
        TradingStatus.HALTED_DRAWDOWN,
        TradingStatus.SLEEPING,
    ]:
        return END

    # If active, proceed to execution
    return "execution_engine"


builder.add_conditional_edges(
    "risk_guardian",
    route_after_risk,
    {
        END: END,
        "execution_engine": "execution_engine",
    },
)

# 5. Execution -> End
builder.add_edge("execution_engine", END)

# Compile
graph = builder.compile()
