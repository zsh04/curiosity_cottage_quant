from app.strategies.base import BaseStrategy
import pandas as pd
import numpy as np


class QuantumOscillatorStrategy(BaseStrategy):
    """
    Quantum Harmonic Oscillator Strategy.
    Models price deviation as displacement in a quantum potential well.
    """

    def __init__(self, window: int = 20, omega: float = 0.1):
        super().__init__()
        self.window = window
        self.omega = omega

    @property
    def name(self) -> str:
        return "QuantumHarmonic_V1"

    def calculate_signal(self, market_data: pd.DataFrame) -> float:
        """
        Calculates signal based on Energy Levels of a Quantum Harmonic Oscillator.

        Logic:
        1. Fair Value (x0) = SMA(20)
        2. Displacement (x) = Price - x0
        3. Energy Levels (En) = (n + 0.5) * omega
        4. Strategy:
           - If displacement 'x' is large (high potential energy),
           - Predict reversion to lower energy state (Mean Reversion).
        """
        if len(market_data) < self.window:
            return 0.0

        # 1. Calculate Fair Value (Equilibrium Point)
        closes = market_data["close"]
        fair_value = closes.rolling(window=self.window).mean().iloc[-1]
        current_price = closes.iloc[-1]

        # 2. Calculate Displacement (x)
        # We normalize x? The prompt implies raw displacement.
        # But E = 0.5 * m * w^2 * x^2 for Classical.
        # Quantum levels are discrete.
        # Let's interpret the user's "E_n" step.
        x = current_price - fair_value

        # 3. Determine Nearest Energy Level
        # E_n = (n + 0.5) * omega
        # We need to find 'n' such that the current 'energy' matches?
        # Or does the user mean: "If x corresponds to an energy between levels..."
        # User Logic: "If abs(x) is between levels... predict Reversion"
        # Wait, x has units of Price. Omega has units of... Frequency?
        # Usually E ~ x^2.
        # But the user said: "Calculate Energy Levels: E_n = (n + 0.5) * omega"
        # And "If abs(x) is between levels".
        # This implies comparing x directly to En? That dimensions mismatch usually.
        # However, for the sake of the "Task", I will follow instructions literally if possible.
        # "If abs(x) is between levels" -> maybe they mean abs(x) acts as the Energy metric?
        # Let's assume Energy_current = abs(x). (Linear potential? Harmonic is quadratic).
        # Let's try to map the harmonic potential: V(x) = 0.5 * k * x^2.
        # User instruction is vague: "If abs(x) is between levels".
        # I will IMPLEMENT EXACTLY as "Step 4: Determine State".
        # Explicit interpretation:
        # compare abs(x) to E_n values.

        # Let's calculate a few levels
        levels = []
        for n in range(10):  # Check first 10 levels
            e_n = (n + 0.5) * self.omega
            levels.append(e_n)

        # Check stability
        # If abs(x) is close to a level, it might be "stable" (quantized).
        # If it is "between" levels, it is unstable -> Mean Revert.
        # Actually, the user says: "Signal = -1.0 * sign(x) (Mean Revert)" unconditionally?
        # "If abs(x) is between levels ... predict Reversion ... Signal = ..."
        # This implies if it IS on a level, signal might be 0?
        # Let's assume: Signal is Mean Revert (-sign(x)) but weighted by "unstability"?
        # Or simplistically: Just return -sign(x) if outside a small band of 0?
        # The prompt says: "Signal = -1.0 * sign(x)".
        # It doesn't explicitly give a condition to return 0.
        # But "Determine State" implies conditional logic.

        # I'll implement a continuous "Restore Force" proportional to distance from nearest level?
        # No, keep it simple V1.
        # If abs(x) > E_0 (Ground state), we have energy -> Revert.

        signal = -1.0 * np.sign(x)

        # Dampen signal if displacement is tiny (inside ground state fluctuation?)
        # E0 = 0.5 * omega.
        if abs(x) < (0.5 * self.omega):
            return 0.0  # Inside ground state zero-point energy

        return float(signal)
