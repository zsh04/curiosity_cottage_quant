import numpy as np
from app.agent.nodes.risk import RiskManager
from app.agent.state import AgentState, TradingStatus


def test_risk_governance():
    print("Testing Risk Governance Protocol...")

    # 1. Test Ruin Check (Drawdown)
    print("\n[Test 1] Max Drawdown > 20%")
    manager = RiskManager()
    state: AgentState = {
        "nav": 100000,
        "cash": 100000,
        "daily_pnl": 0,
        "max_drawdown": 0.25,  # 25% drawdown
        "current_alpha": 4.0,
        "regime": "Gaussian",
        "status": TradingStatus.ACTIVE,
        "messages": [],
    }

    new_state = manager.check_governance(state)
    if new_state["status"] == TradingStatus.HALTED_DRAWDOWN:
        print("PASS: Trading Halted due to Drawdown.")
    else:
        print(f"FAIL: Status is {new_state['status']}")

    # 2. Test Daily Stop
    print("\n[Test 2] Daily Loss > 2%")
    state["max_drawdown"] = 0.0
    state["daily_pnl"] = -2500  # -2.5% of 100k NAV
    state["status"] = TradingStatus.ACTIVE

    new_state = manager.check_governance(state)
    if new_state["status"] == TradingStatus.SLEEPING:
        print("PASS: Trading Halted due to Daily Stop.")
    else:
        print(f"FAIL: Status is {new_state['status']}")

    # 3. Test Physics Veto (Alpha <= 2.0)
    print("\n[Test 3] Physics Veto (Alpha = 1.5)")
    state["daily_pnl"] = 0
    state["status"] = TradingStatus.ACTIVE

    # Simulate heavy tail returns
    returns = np.random.pareto(a=1.5, size=1000)  # Pareto with alpha 1.5

    new_state = manager.update_physics(state, returns)
    if new_state["status"] == TradingStatus.HALTED_PHYSICS:
        print(
            f"PASS: Trading Halted due to Critical Regime (Alpha {new_state['current_alpha']:.2f})."
        )
    else:
        print(f"FAIL: Status is {new_state['status']}")

    # 4. Test Sizing (Gaussian Regime)
    print("\n[Test 4] Sizing in Gaussian Regime (Alpha > 3)")
    returns_gaussian = np.random.normal(0, 0.01, 1000)
    state["current_alpha"] = 4.0
    state["nav"] = 100000

    size = manager.calculate_position_size(state, returns_gaussian)
    print(f"Output Size: ${size:,.2f}")
    assert size > 0, "Size should be positive in Gaussian regime"
    print("PASS: Positive size returned.")


if __name__ == "__main__":
    test_risk_governance()
