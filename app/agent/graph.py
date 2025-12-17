from langgraph.graph import StateGraph, END
from app.agent.state import AgentState, TradingStatus

# New "Sensor Fusion" Nodes
from app.agent.nodes.analyst import analyst_node
from app.agent.nodes.risk import risk_node
from app.agent.nodes.macro import macro_node  # Add Macro

# Assuming execution_node exists and is correct
from app.agent.nodes.execution import execution_node

# Start Graph Construction
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("macro", macro_node)  # Register Macro
workflow.add_node("analyst", analyst_node)
workflow.add_node("risk", risk_node)
workflow.add_node("execution", execution_node)

# Edges
# Macro is now the entry point (Scanner)
workflow.set_entry_point("macro")

# Macro -> Analyst
workflow.add_edge("macro", "analyst")

workflow.add_edge("analyst", "risk")


def check_veto(state: AgentState):
    status = state.get("status")
    if status in [TradingStatus.HALTED_PHYSICS, TradingStatus.HALTED_DRAWDOWN]:
        print(f"--- Graph Decision: HALT ({status}) ---")
        return "end"
    return "execution"


workflow.add_conditional_edges(
    "risk", check_veto, {"end": END, "execution": "execution"}
)

workflow.add_edge("execution", END)

app_graph = workflow.compile()
