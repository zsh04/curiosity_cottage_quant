from langgraph.graph import StateGraph, END
from app.agent.state import AgentState, TradingStatus

# New "Sensor Fusion" Nodes
from app.agent.nodes.analyst import analyst_node
from app.agent.nodes.risk import risk_node

# Assuming execution_node exists and is correct
from app.agent.nodes.execution import execution_node

# Start Graph Construction
workflow = StateGraph(AgentState)

# Nodes
# Note: Macro layer might be bypassed or using legacy if not refactored yet.
# Given the user says "remove ... not require any longer", and we heavily focused on Analyst->Risk->Execution pipeline.
# Usually Analyst is the entry point in simplified "Sensor Fusion" without Macro global view.
# However, the previous graph had Macro as entry.
# Without a new Macro node, I will set Analyst as Entry Point as per "Analyst Node... implements full Sensor Fusion pipeline".

workflow.add_node("analyst", analyst_node)
workflow.add_node("risk", risk_node)
workflow.add_node("execution", execution_node)

# Edges
workflow.set_entry_point("analyst")

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
