from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.macro_agent import macro_agent
from app.agent.analyst_agent import analyst_agent

# from app.agent.execution_agent import execution_agent # REPLACED
from app.agent.risk_agent import risk_agent

# Define Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("macro", macro_agent)
workflow.add_node("analyst", analyst_agent)
# workflow.add_node("execution", execution_agent)
workflow.add_node("risk", risk_agent)

# Add Edges
workflow.set_entry_point("macro")

workflow.add_edge("macro", "analyst")
# workflow.add_edge("analyst", "execution")
workflow.add_edge("analyst", "risk")
# workflow.add_edge("execution", END)
workflow.add_edge("risk", END)

# Compile
app_graph = workflow.compile()
