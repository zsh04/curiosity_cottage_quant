from langgraph.graph import StateGraph, END
from app.agent.state import AgentState, TradingStatus
from app.agent.macro_agent import macro_agent
from app.agent.analyst_agent import analyst_agent
from app.agent.nodes.risk import risk_node
from app.agent.nodes.execution import execution_node

# Define Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("macro", macro_agent)
workflow.add_node("analyst", analyst_agent)
workflow.add_node("risk", risk_node)
workflow.add_node("execution", execution_node)

# Add Edges
workflow.set_entry_point("macro")

workflow.add_edge("macro", "analyst")
workflow.add_edge("analyst", "risk")


# Conditional Logic for Risk Veto
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

# Compile
app_graph = workflow.compile()
