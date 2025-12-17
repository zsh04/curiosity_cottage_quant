import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import os

# Ensure app imports work
sys.path.append(os.getcwd())

# Mock missing dependencies
sys.modules["langgraph"] = MagicMock()
sys.modules["langgraph.graph"] = MagicMock()
sys.modules["langchain"] = MagicMock()
sys.modules["langchain_core"] = MagicMock()
sys.modules["langchain_core.prompts"] = MagicMock()
sys.modules["langchain_core"] = MagicMock()
sys.modules["langchain_core.prompts"] = MagicMock()
sys.modules["langchain_openai"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["pandas"] = MagicMock()


class MockSeries(list):
    pass


class MockDataFrame(dict):
    pass


mock_pd = MagicMock()
mock_pd.Series = MockSeries
mock_pd.DataFrame = MockDataFrame
sys.modules["pandas"] = mock_pd

sys.modules["numpy"] = MagicMock()
sys.modules["scipy"] = MagicMock()
sys.modules["scipy.stats"] = MagicMock()
sys.modules["alpaca"] = MagicMock()
sys.modules["alpaca"] = MagicMock()
sys.modules["alpaca.data"] = MagicMock()
sys.modules["alpaca.data.historical"] = MagicMock()
sys.modules["alpaca.data.requests"] = MagicMock()
sys.modules["alpaca.data.timeframe"] = MagicMock()
sys.modules["alpaca.trading"] = MagicMock()
sys.modules["alpaca.trading.client"] = MagicMock()
sys.modules["alpaca.trading.requests"] = MagicMock()
sys.modules["alpaca.trading.enums"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["transformers"] = MagicMock()
sys.modules["scikit-learn"] = MagicMock()
sys.modules["sklearn"] = MagicMock()
sys.modules["opentelemetry"] = MagicMock()
sys.modules["opentelemetry.trace"] = MagicMock()
sys.modules["opentelemetry.sdk"] = MagicMock()
sys.modules["opentelemetry.sdk.trace"] = MagicMock()
sys.modules["opentelemetry.sdk.trace"] = MagicMock()
sys.modules["opentelemetry.exporter.otlp.proto.grpc"] = MagicMock()
sys.modules["requests"] = MagicMock()
sys.modules["urllib3"] = MagicMock()
sys.modules["pydantic"] = MagicMock()
sys.modules["pydantic_settings"] = MagicMock()
sys.modules["openai"] = MagicMock()

# Mock internal libraries to avoid complex logic execution
sys.modules["app.lib.memory"] = MagicMock()
sys.modules["app.lib.physics"] = MagicMock()
sys.modules["app.lib.physics.heavy_tail"] = MagicMock()
# Also mock adapters to prevent initialization logic
sys.modules["app.adapters.market"] = MagicMock()
sys.modules["app.adapters.llm"] = MagicMock()
sys.modules["app.adapters.sentiment"] = MagicMock()
sys.modules["app.adapters.chronos"] = MagicMock()
sys.modules["app.lib.kalman"] = MagicMock()

from app.agent.nodes.analyst import AnalystAgent
from app.agent.state import AgentState, OrderSide


class TestConfidenceWeighting(unittest.TestCase):
    def setUp(self):
        self.agent = AnalystAgent()

        # Mock dependencies to avoid external calls
        self.agent.market = MagicMock()
        self.agent.llm = MagicMock()
        self.agent.sentiment = MagicMock()
        self.agent.chronos = MagicMock()
        self.agent.kf = MagicMock()
        self.agent.physics = MagicMock()

        # Standard Mocks
        self.agent.market.get_current_price.return_value = 100.0
        self.agent.market.get_historic_returns.return_value = [0.01] * 30
        self.agent.llm.get_trade_signal.return_value = {
            "signal_side": "BUY",
            "signal_confidence": 0.5,
            "reasoning": "Test signal",
        }

        # Mocking generic Physics/Hurst to avoid noise mode
        # We need Hurst > 0.55 for TREND
        # We will mock the internal methods directly in the test cases or patch them

        # Configure mocks to return valid data types
        # Market
        self.agent.market.get_latest_price.return_value = 100.0
        self.agent.market.get_history.return_value = [100.0] * 100

        # Chronos - Mock on Class level ensure instance gets it
        mock_chronos_cls = sys.modules["app.adapters.chronos"].ChronosAdapter
        forecast_data = {"median": [101.0], "low": [99.0], "high": [103.0]}
        mock_chronos_cls.return_value.predict.return_value = forecast_data
        self.agent.chronos.predict.return_value = forecast_data  # Instance too

        # Helper to create clean state
        from types import SimpleNamespace

        self.kf_state = SimpleNamespace(velocity=0.5, acceleration=0.1, position=100.0)

        # DIRECTLY configure the mocks
        # KF is accessed via self.kf (Instance Attribute)
        # So we MUST mock the instance on the agent itself
        self.agent.kf = MagicMock()
        self.agent.kf.update.return_value = self.kf_state

        # HeavyTail is accessed via Class Static Methods (Global)
        # So we mock the imported class in the module
        import app.agent.nodes.analyst as analyst_module

        mock_ht_cls = MagicMock()
        mock_ht_cls.hill_estimator.return_value = 1.6
        mock_ht_cls.detect_regime.return_value = "Gaussian"
        analyst_module.HeavyTailEstimator = mock_ht_cls

        # Sentiment
        self.agent.sentiment.analyze_news.return_value = 0.5

        # Memory
        mock_fractal = sys.modules["app.lib.memory"].FractalMemory
        mock_fractal.frac_diff.return_value = MagicMock()

        # Initialize a base mock_state for tests to modify
        self.mock_state = AgentState(
            symbol="SPY",
            price=100.0,
            historic_returns=[],
            performance_metrics={},
            messages=[],
            strategy_mode="DEFAULT",
            signal_confidence=0.5,
            signal_side=OrderSide.BUY,
            reasoning="Initial reasoning",
        )

    def tearDown(self):
        pass

    @patch("app.lib.memory.FractalMemory.calculate_hurst")
    def test_high_performance_boost(self, mock_hurst):
        # DEBUG: Verify mock
        print(
            f"DEBUG: Chronos Forecast Mock Return: {self.agent.chronos.predict([], 10)}"
        )

        # Case 1: High Trend Win Rate (80%) -> Should boost confidence
        mock_hurst.return_value = 0.6  # Trend Regime

        # Override state for this specific test case
        self.mock_state["performance_metrics"] = {"trend_win_rate": 0.8}
        self.mock_state["strategy_mode"] = "TREND"
        self.mock_state["signal_confidence"] = 0.5  # Base confidence

        result_state = self.agent.analyze(self.mock_state)

        print(f"DEBUG: Result State: {result_state}")
        # Expected = 0.5 * 1.6 = 0.8

        self.assertEqual(result_state["strategy_mode"], "TREND")
        self.assertAlmostEqual(result_state["signal_confidence"], 0.8)
        print(
            f"✅ High Perf Test Passed: Conf 0.5 -> {result_state['signal_confidence']}"
        )

    @patch("app.lib.memory.FractalMemory.calculate_hurst")
    def test_low_performance_penalty(self, mock_hurst):
        # Case 2: Low Trend Win Rate (40%) -> Should penalize confidence
        mock_hurst.return_value = 0.6  # TREND mode

        state = AgentState(
            symbol="SPY",
            price=100.0,
            historic_returns=[],
            performance_metrics={"trend_win_rate": 0.4},
            messages=[],
        )

        # Raw confidence is 0.5
        # Multiplier = 0.4 / 0.5 = 0.8
        # Expected = 0.5 * 0.8 = 0.4

        result_state = self.agent.analyze(state)

        self.assertEqual(result_state["strategy_mode"], "TREND")
        self.assertAlmostEqual(result_state["signal_confidence"], 0.4)
        print(
            f"✅ Low Perf Test Passed: Conf 0.5 -> {result_state['signal_confidence']}"
        )

    @patch("app.lib.memory.FractalMemory.calculate_hurst")
    def test_neutral_default(self, mock_hurst):
        # Case 3: No metrics -> Should stay same
        mock_hurst.return_value = 0.6  # TREND mode

        state = AgentState(
            symbol="SPY",
            price=100.0,
            historic_returns=[],
            performance_metrics={},  # Empty
            messages=[],
        )

        # Multiplier = 0.5 / 0.5 = 1.0 (Default)
        # Expected = 0.5

        result_state = self.agent.analyze(state)

        self.assertAlmostEqual(result_state["signal_confidence"], 0.5)
        print(f"✅ Neutral Test Passed: Conf {result_state['signal_confidence']}")


if __name__ == "__main__":
    unittest.main()
