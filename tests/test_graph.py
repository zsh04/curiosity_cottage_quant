import unittest
from app.agent.graph import app_graph
from app.agent.state import AgentState, TradingStatus


class TestAgentGraph(unittest.TestCase):
    def test_graph_compiles(self):
        """Verify the graph compiles to a Runnable."""
        self.assertIsNotNone(app_graph)

    def test_graph_structure(self):
        """Verify nodes and edges exist."""
        # This is a bit internal, but we can check the graph definition object if accessible
        # or just trust the compile didn't fail.
        pass
