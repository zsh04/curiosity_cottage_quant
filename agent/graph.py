from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.macro.agent import MacroAgent
from agent.risk.agent import RiskAgent


class TradingGraph:
    """
    Orchestrator for the Curiosity Cottage Quantitative Protocol.
    """

    def __init__(self):
        self.workflow = StateGraph(AgentState)
        self._build_graph()

    def _build_graph(self):
        # 1. Add Nodes
        self.workflow.add_node("macro_analyst", MacroAgent.analyze_regime)
        self.workflow.add_node("risk_guardian", RiskAgent.physics_veto)

        # 2. Add Edges
        # Start -> Macro Analyst
        self.workflow.set_entry_point("macro_analyst")

        # Macro Analyst -> Risk Guardian
        self.workflow.add_edge("macro_analyst", "risk_guardian")

        # Risk Guardian -> END (for now, until Execution Agent is added)
        self.workflow.add_edge("risk_guardian", END)

    def compile(self):
        """Compiles the graph into a runnable application."""
        return self.workflow.compile()
