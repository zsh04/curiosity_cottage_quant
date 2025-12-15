import unittest
from app.agent.graph import app_graph
from app.agent.state import AgentState, TradingStatus


class TestAgentGraph(unittest.TestCase):
    def test_graph_flow_happy_path(self):
        # Initial State
        initial_state: AgentState = {
            "messages": [],
            "nav": 1000.0,
            "cash": 1000.0,
            "daily_pnl": 0.0,
            "max_drawdown": 0.0,
            "current_alpha": 4.0,  # Gaussian
            "regime": "Gaussian",
            "status": TradingStatus.ACTIVE,
        }

        # Run graph
        # Since we don't have async runner setup easily in unittest without external libs or mocking,
        # we will test the nodes individually or use graph.invoke if synchronous.
        # LangGraph invoke is synchronous by default for StateGraph.

        result = app_graph.invoke(initial_state)

        # Verify messages contain output from all agents
        messages = result["messages"]
        self.assertTrue(any("MACRO" in m for m in messages))
        self.assertTrue(any("ANALYST" in m for m in messages))
        # EXECUTION should run if risk permits
        self.assertTrue(any("EXECUTION" in m for m in messages))

    def test_risk_veto(self):
        # Initial State with CRITICAL regime
        initial_state: AgentState = {
            "messages": [],
            "nav": 1000.0,
            "cash": 1000.0,
            "daily_pnl": 0.0,
            "max_drawdown": 0.0,
            "current_alpha": 1.5,  # CRITICAL (< 2.0)
            "regime": "Critical",
            "status": TradingStatus.ACTIVE,
        }

        # The graph will run: Macro -> Analyst -> Risk (Vetos) -> End
        # Execution should NOT run

        result = app_graph.invoke(initial_state)

        messages = result["messages"]
        self.assertTrue(any("PHYSICS VETO" in m for m in messages))
        self.assertFalse(any("EXECUTION" in m for m in messages))
        self.assertEqual(result["status"], TradingStatus.HALTED_PHYSICS)


if __name__ == "__main__":
    unittest.main()
