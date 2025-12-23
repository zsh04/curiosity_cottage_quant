import unittest
from app.agent.nash import NashAgent
from app.agent.state import AgentState


class TestNashAllocator(unittest.TestCase):
    def setUp(self):
        self.agent = NashAgent()

    def test_settlement_veto(self):
        """
        Test that Nash VETOES a BUY when Buying Power is insufficient (T+1 Lock).
        """
        state: AgentState = {
            "symbol": "BTC/USD",
            "signal_side": "BUY",
            "buying_power": 5.0,  # < $20 Threshold
            "reasoning": "Test Signal",
            "candidates": [],
        }

        # Run Audit
        result = self.agent.audit(state)

        # Assertions
        self.assertEqual(
            result["signal_side"],
            "FLAT",
            "Signal should be flattened by Settlement Lock",
        )
        self.assertIn("Settlement Lock", result["reasoning"])
        print("\n✅ Settlement Lock Veto: PASSED")

    def test_settlement_pass(self):
        """
        Test that Nash APPROVES a BUY when Buying Power is sufficient.
        """
        state: AgentState = {
            "symbol": "BTC/USD",
            "signal_side": "BUY",
            "buying_power": 500.0,  # > $20 Threshold
            "reasoning": "Test Signal",
            "candidates": [
                {"symbol": "BTC/USD", "physics_vector": {"nash_dist": 0.5}}
            ],  # Low Nash Dist
        }

        # Run Audit
        result = self.agent.audit(state)

        # Assertions
        self.assertEqual(
            result["signal_side"], "BUY", "Signal should persist with funds"
        )
        print("\n✅ Settlement Liquidity Check: PASSED")


if __name__ == "__main__":
    unittest.main()
