import logging
import time
from typing import Optional
from app.agent.state import AgentState, TradingStatus, OrderSide
from app.lib.physics import Regime
from app.services.global_state import get_global_state_service, get_current_snapshot_id

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Enforces the 'Iron Gate' Protocol:
    1. Governance: Hard checks on Drawdown and Regime.
    2. Sizing: Bayesian sizing based on Volatility Stop + Physics Scalar.
    """

    def __init__(self, max_drawdown_limit: float = 0.20):
        self.max_drawdown_limit = max_drawdown_limit

    def check_governance(self, state: AgentState) -> AgentState:
        """
        Hard Stops. If breached, status -> HALTED.
        """
        # 1. Ruin Check
        if state.get("max_drawdown", 0.0) >= self.max_drawdown_limit:
            state["status"] = TradingStatus.HALTED_DRAWDOWN
            msg = f"CRITICAL: Max Drawdown {state['max_drawdown']:.1%} breached limit. FIRM FAILURE."
            state["messages"].append(msg)
            return state

        # 2. Physics Veto
        regime = state.get("regime", "Unknown")
        if regime == Regime.CRITICAL.value:
            state["status"] = TradingStatus.HALTED_PHYSICS
            msg = f"PHYSICS VETO: Critical Regime detected. Trading Halted."
            state["messages"].append(msg)
            return state

        # If all good, ensure Active
        if state.get("status") not in [
            TradingStatus.HALTED_PHYSICS,
            TradingStatus.HALTED_DRAWDOWN,
        ]:
            state["status"] = TradingStatus.ACTIVE

        return state

    def size_position(self, state: AgentState) -> float:
        """
        Bayesian Sizing Logic.
        Base Size = Risk 1% of NAV with 2% Stop.
        """
        nav = state.get("nav", 100000.0)
        alpha = state.get("current_alpha", 2.0)
        confidence = state.get("signal_confidence", 0.0)

        # 1. Base Size
        base_size = (nav * 0.01) / 0.02

        # 2. Physics Scalar
        physics_scalar = min(1.0, max(0.0, alpha - 1.5))

        # 3. Final Calculation
        approved_size = base_size * confidence * physics_scalar

        return approved_size


def risk_node(state: AgentState) -> AgentState:
    manager = RiskManager()
    start_time = time.time()
    success = True
    error_msg = None

    try:
        # 1. Update Governance Status
        state = manager.check_governance(state)

        status = state.get("status", TradingStatus.ACTIVE)
        signal_side = state.get("signal_side", OrderSide.FLAT.value)

        # 2. The Logic Branch
        if status != TradingStatus.ACTIVE:
            state["approved_size"] = 0.0
        elif signal_side in [OrderSide.BUY.value, OrderSide.SELL.value]:
            # Active + Signal -> Check Sizing
            size = manager.size_position(state)
            state["approved_size"] = size

            alpha = state.get("current_alpha", 0.0)
            log_msg = f"RISK: ✅ Approved ${size:.2f} (Alpha: {alpha:.2f})"
            print(log_msg)
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(log_msg)
        else:
            # FLAT or Invalid
            state["approved_size"] = 0.0

    except Exception as e:
        success = False
        error_msg = f"RISK: 💥 CRASH: {e}"
        print(error_msg)
        logger.exception(error_msg)
        state["approved_size"] = 0.0
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append(error_msg)

    finally:
        # TRACK RISK NODE PERFORMANCE
        latency = (time.time() - start_time) * 1000
        state_service = get_global_state_service()
        snapshot_id = get_current_snapshot_id()
        if state_service and snapshot_id:
            state_service.save_agent_metrics(
                snapshot_id=snapshot_id,
                agent_name="risk",
                latency_ms=latency,
                success=success,
                output_data={
                    "approved_size": state.get("approved_size"),
                    "status": str(state.get("status")),
                    "alpha": state.get("current_alpha"),
                    "regime": state.get("regime"),
                },
                error=error_msg,
            )

    return state
