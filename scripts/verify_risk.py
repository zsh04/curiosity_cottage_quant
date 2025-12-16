import sys
import os
import numpy as np
from typing import Dict, Any

# Add project root to path
sys.path.append(os.getcwd())

from app.agent.nodes.risk import risk_node
from app.agent.state import AgentState, TradingStatus, OrderSide


def create_mock_state(
    alpha: float, forecast: Dict[str, Any], price: float = 100.0
) -> AgentState:
    return {
        "nav": 100000.0,
        "cash": 100000.0,
        "daily_pnl": 0.0,
        "max_drawdown": 0.0,
        "symbol": "MOCK",
        "price": price,
        "historic_returns": [],
        "current_alpha": alpha,
        "regime": "Unknown",
        "signal_side": OrderSide.BUY.value,
        "signal_confidence": 1.0,
        "reasoning": "Test",
        "approved_size": 0.0,
        "risk_multiplier": 1.0,
        "status": TradingStatus.ACTIVE,
        "messages": [],
        "chronos_forecast": forecast,
    }


def verify_risk_node():
    print("⚖️ Verifying Risk Node Constitutional Compliance...\n")

    # --- Scenario A: Safe (Gaussian, Low Vol) ---
    print("🔹 Scenario A: Safe (Alpha=3.5, Low Volatility)")
    forecast_safe = {
        "median": np.array([102.0]),  # +2% Return
        "low": np.array([99.0]),
        "high": np.array([105.0]),  # Spread 6 -> Sigma ~2.3
    }
    state_a = create_mock_state(alpha=3.5, forecast=forecast_safe)
    state_a = risk_node(state_a)
    size_a = state_a.get("approved_size", 0.0)
    print(f"   Output Size: ${size_a:,.2f}")

    assert size_a > 0.0, "Scenario A should have approved size > 0"
    print("   ✅ PASSED: Positive allocation in Gaussian regime.\n")

    # --- Scenario B: Heavy Tail (Critical) ---
    print("🔹 Scenario B: Heavy Tail (Alpha=1.5, Critical)")
    # Same forecast, but Alpha indicates infinite variance regime
    state_b = create_mock_state(alpha=1.5, forecast=forecast_safe)
    state_b = risk_node(state_b)
    size_b = state_b.get("approved_size", 0.0)
    print(f"   Output Size: ${size_b:,.2f}")

    assert size_b == 0.0, "Scenario B must be VETOED (Size 0.0)"
    print("   ✅ PASSED: Physics Veto enforced for Alpha <= 2.0.\n")

    # --- Scenario C: High Variance (Transition) ---
    print("🔹 Scenario C: High Risk (Alpha=3.0, High Volatility)")
    forecast_risky = {
        "median": np.array([102.0]),  # Same +2% Return
        "low": np.array([90.0]),
        "high": np.array([114.0]),  # Spread 24 -> Sigma ~9.3 (4x riskier)
    }
    state_c = create_mock_state(alpha=3.0, forecast=forecast_risky)
    state_c = risk_node(state_c)
    size_c = state_c.get("approved_size", 0.0)
    print(f"   Output Size Scenario A (Safe): ${size_a:,.2f}")
    print(f"   Output Size Scenario C (Risky): ${size_c:,.2f}")

    assert size_c > 0.0, "Scenario C should still trade (Alpha 3.0 is valid)"
    assert size_c < size_a, (
        f"Scenario C (${size_c}) must be smaller than A (${size_a}) due to higher ES"
    )
    print("   ✅ PASSED: Volatility dampening confirmed (Risky size < Safe size).\n")

    print("✅ All Constitutional Checks Passed.")


if __name__ == "__main__":
    verify_risk_node()
