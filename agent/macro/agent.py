from agent.state import AgentState
from lib.physics.heavy_tail import HeavyTailEstimator
import pandas as pd
import numpy as np


class MacroAgent:
    """
    The 'Analyst' or 'Macro' agent.
    Responsibility: Identify the broad market regime (Gaussian vs Levy).
    Mechanism: Uses Hill Estimator on recent price returns.
    """

    @staticmethod
    def analyze_regime(state: AgentState) -> AgentState:
        """
        Node function to analyze market data and update regime state.
        """
        print("--- MACRO AGENT: Analyzing Regime ---")

        # Extract data (Mocking data extraction for now, assuming pre-loaded in state or fetching from DB)
        # In a real run, this would query TimescaleDB via the 'market_data' key pointers
        market_data = state.get("market_data", {})
        prices = market_data.get("prices", [])

        if not prices or len(prices) < 30:
            # Insufficient data, default to safe mode or assume Gaussian
            print("Insufficient data for Hill Estimator.")
            return {"alpha": 3.0, "regime": "GAUSSIAN"}

        # Calculate Returns
        series = pd.Series(prices)
        returns = series.pct_change().dropna().values

        # Physics Engine Calculation
        alpha = HeavyTailEstimator.hill_estimator(returns)
        regime = HeavyTailEstimator.detect_regime(alpha)

        print(f"Detected Alpha: {alpha:.2f} | Regime: {regime}")

        # Update State
        return {"alpha": alpha, "regime": regime}
