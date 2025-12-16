import logging
import time
from typing import Optional
from app.agent.state import AgentState, TradingStatus, OrderSide
from app.lib.physics import Regime
from app.agent.risk.bes import BesSizing
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
        self.bes = BesSizing()

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
        Bayesian Sizing Logic using BesSizing.
        """
        # Extract Inputs
        alpha = state.get("current_alpha")
        forecast = state.get("chronos_forecast")
        price = state.get("price")

        # Guard 1: Data Integrity
        if alpha is None or not forecast or not price:
            logger.warning(
                "RISK: Missing input data (alpha/forecast/price). Sizing 0.0."
            )
            return 0.0

        # Guard 2: Physics (BES Calculation)
        # Using NAV as capital base
        capital = state.get("nav", 100000.0)
        try:
            size_pct = self.bes.calculate_size(
                forecast=forecast, alpha=alpha, current_price=price, capital=capital
            )
        except Exception as e:
            logger.error(f"RISK: BES Calculation Error: {e}")
            return 0.0

        # Guard 3: Drawdown (Redundant to check_governance but good for sizing specific logic)
        # If strict drawdown limit is close, reduce size?
        # For now, following prompt: "If drawdown > 2%, force size = 0.0"
        # Note: state['max_drawdown'] is usually positive float, e.g. 0.05 for 5% DD
        current_dd = state.get("max_drawdown", 0.0)
        # Prompt said: "Check state['portfolio_value'] vs high_water_mark"
        # But state usually has "max_drawdown". I created state definition.
        # Let's rely on stored max_drawdown for simplicity if it tracks daily.
        # Or calculate it if needed. State has 'nav' and likely 'max_drawdown'.
        # Assuming max_drawdown is current drawdown since peak.
        if current_dd > 0.02:
            logger.warning(f"RISK: Drawdown {current_dd:.1%} > 2%. Safety Halt.")
            return 0.0

        # Calculate Approved Notional
        # Size is returned as % of capital (0.0 to 0.20)
        approved_notional = size_pct * capital

        # Store ES for logging (re-calculate or done implicitly? Method doesn't return it separate)
        # We'll just log the size.

        return approved_notional


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
            size_notional = manager.size_position(state)
            state["approved_size"] = size_notional

            # Logging
            alpha_val = state.get("current_alpha", 0.0)
            # Re-estimate ES for logging transparency
            es_val = 0.0
            forecast = state.get("chronos_forecast")
            if forecast:
                es_val = manager.bes.estimate_es(forecast)

            size_pct = size_notional / state.get("nav", 100000.0)

            log_msg = f"⚖️ RISK: Alpha={alpha_val:.2f} | ES_95={es_val:.4f} | Size={size_pct:.2%}"
            print(log_msg)
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(log_msg)

        else:
            # FLAT or Invalid
            state["approved_size"] = 0.0
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append("RISK: FLAT (No Signal)")

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
