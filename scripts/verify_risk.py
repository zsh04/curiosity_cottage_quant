import numpy as np
import logging
from app.agent.nodes.taleb import risk_node, RiskManager
from app.agent.state import AgentState, TradingStatus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_RISK")


def test_risk_governance():
    print("Testing Risk Governance Protocol...")

    # 1. Test Ruin Check (Drawdown)
    print("\n[Test 1] Max Drawdown > 2% (Circuit Breaker)")
    manager = RiskManager()
    state: AgentState = {
        "nav": 100000,
        "cash": 100000,
        "starting_capital": 100000,
        "daily_pnl": 0,
        "max_drawdown": 0.03,  # 3% drawdown > 2% limit
        "current_alpha": 4.0,
        "regime": "Gaussian",
        "status": TradingStatus.ACTIVE,
        "messages": [],
    }

    new_state = manager.check_circuit_breaker(state)
    if new_state["status"] == TradingStatus.HALTED_DRAWDOWN:
        print("✅ PASS: Trading Halted due to Drawdown.")
    else:
        print(f"❌ FAIL: Status is {new_state['status']}")

    # 2. Daily Stop (REMOVED in Taleb V1)
    print("\n[Test 2] Daily Loss > 2% (Skipped - Not Active)")
    # manager.check_circuit_breaker only checks total drawdown now

    # 3. Test Physics (Fractal Sizing Check)
    # The Physics Veto is now "Soft" (Warning only), actual reduction happens in sizing.
    print("\n[Test 3] Physics Veto -> Fractal Sizing (Alpha = 1.5)")
    state["max_drawdown"] = 0.0
    state["status"] = TradingStatus.ACTIVE
    state["regime"] = "Critical"  # Trigger check_physics_veto warning
    state["current_alpha"] = 1.5
    state["symbol"] = "TEST"

    # A. Check Veto Logic (Should NOT Halt)
    new_state = manager.check_physics_veto(state)
    if new_state["status"] != TradingStatus.HALTED_PHYSICS:
        print(
            f"✅ PASS: Trading NOT Halted for Critical Regime (Fractal Sizing Active). Status: {new_state['status']}"
        )
    else:
        print(f"❌ FAIL: Status HALTED unexpectedly: {new_state['status']}")

    # 4. Test Sizing (Gaussian Regime)
    print("\n[Test 4] Sizing in Gaussian Regime (Alpha > 3)")
    state["regime"] = "Gaussian"
    state["current_alpha"] = 4.0
    state["status"] = TradingStatus.ACTIVE
    state["signal_side"] = "BUY"
    state["price"] = 100.0
    # Mock forecast required for BES
    state["chronos_forecast"] = {
        "median": [105.0],  # 5% return
        "low": [98.0],
        "high": [112.0],
    }
    state["current_positions"] = []  # prevent entanglement check fail

    size_notional = manager.size_position(state)
    print(f"Output Size: ${size_notional:,.2f}")
    assert size_notional > 0, "Size should be positive in Gaussian regime"
    print("✅ PASS: Positive size returned.")


if __name__ == "__main__":
    test_risk_governance()
