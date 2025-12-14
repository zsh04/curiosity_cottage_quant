import pytest
import numpy as np
from agent.state import AgentState
from agent.macro.agent import MacroAgent
from agent.risk.agent import RiskAgent
from agent.graph import TradingGraph


class TestCognitiveCore:
    def test_macro_agent_gaussian(self):
        """Test Macro Agent with Gaussian data"""
        np.random.seed(42)
        # Low volatility Gaussian data, Price > 0 to avoid zero-division in returns
        # Increase sample size for stable estimation
        prices = 100.0 + np.cumsum(np.random.normal(0, 1, 5000))

        state = {"market_data": {"prices": prices.tolist()}}
        result = MacroAgent.analyze_regime(state)

        assert result["regime"] == "GAUSSIAN"
        assert result["alpha"] > 2.0

    def test_macro_agent_insufficient_data(self):
        state = {"market_data": {"prices": [1, 2, 3]}}
        result = MacroAgent.analyze_regime(state)
        assert result["regime"] == "GAUSSIAN"  # Default safe mode

    def test_risk_agent_veto(self):
        """Test Physics Veto logic"""
        # Case 1: Levy Regime -> VETO
        state_levy = {"regime": "LEVY", "trade_decision": "BUY"}
        result_levy = RiskAgent.physics_veto(state_levy)
        assert result_levy["trade_decision"] == "VETO_PHYSICS"
        assert result_levy["risk_score"] == 100.0

        # Case 2: Gaussian Regime -> Pass
        state_gaussian = {"regime": "GAUSSIAN", "trade_decision": "BUY"}
        result_gaussian = RiskAgent.physics_veto(state_gaussian)
        assert "trade_decision" not in result_gaussian  # Should not overwrite
        assert result_gaussian["risk_score"] == 0.0

    def test_graph_compilation(self):
        """Verify the graph compiles without errors"""
        graph = TradingGraph()
        app = graph.compile()
        assert app is not None
