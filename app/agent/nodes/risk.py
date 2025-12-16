import logging
from app.agent.state import AgentState, TradingStatus, OrderSide
from app.lib.physics import Regime

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
        # If the Analyst or background process set regime to critical, we halt.
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
        nav = state.get("nav", 100000.0)  # Default if missing
        alpha = state.get("current_alpha", 2.0)
        confidence = state.get("signal_confidence", 0.0)

        # 1. Base Size
        # "Risk 1% of NAV / 0.02 stop" -> (NAV * 0.01) / 0.02 = NAV * 0.5
        # This basically means 50% leverage if confidence is 1.0 and alpha is perfect.
        base_size = (nav * 0.01) / 0.02

        # 2. Physics Scalar
        # Scale down if Alpha is low (risky).
        # Alpha < 1.5 is entering heavy tail territory.
        # If Alpha >= 2.5 (Gaussian), scalar = 1.0.
        # If Alpha = 1.5, scalar = 0.0.
        # wait, the request said: max(0.0, alpha - 1.5).
        # So at Alpha=2.0 (Lévy), scalar = 0.5. At Alpha=1.5, scalar=0.0.
        # But we also clamp at 1.0? "min(1.0, ...)" implicitly if we follow common sense,
        # but request formula is just "min(1.0, max(0.0, alpha - 1.5))".
        physics_scalar = min(1.0, max(0.0, alpha - 1.5))

        # 3. Final Calculation
        approved_size = base_size * confidence * physics_scalar

        return approved_size


def risk_node(state: AgentState) -> AgentState:
    manager = RiskManager()

    # 1. Update Governance Status
    state = manager.check_governance(state)

    status = state.get("status", TradingStatus.ACTIVE)
    signal_side = state.get("signal_side", OrderSide.FLAT.value)

    # 2. The Logic Branch
    if status != TradingStatus.ACTIVE:
        state["approved_size"] = 0.0
        # Optional: Log that we are halted? Governance check already logs breaches.
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

    return state
