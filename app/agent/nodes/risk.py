from typing import Dict, Any
import numpy as np
from app.agent.state import AgentState, TradingStatus
from app.lib.physics import HeavyTailEstimator, Regime, expected_shortfall


class RiskManager:
    """
    Enforces the Risk Governance Protocol.
    1. Capital Preservation (Ruin/DayStop)
    2. Physics Veto (Alpha Regime)
    3. Position Sizing (ES-Kelly)
    """

    def __init__(
        self,
        max_drawdown_limit: float = 0.20,
        daily_stop_limit: float = 0.02,
        kelly_fraction: float = 0.5,
    ):
        self.max_drawdown_limit = max_drawdown_limit
        self.daily_stop_limit = daily_stop_limit
        self.kelly_fraction = kelly_fraction
        self.estimator = HeavyTailEstimator()

    def check_governance(self, state: AgentState) -> AgentState:
        """
        Main entry point for Risk Governance.
        Checks hard stops first, then regimes.
        """
        # 1. Capital Preservation Checks
        # Ruin Check
        if state["max_drawdown"] >= self.max_drawdown_limit:
            state["status"] = TradingStatus.HALTED_DRAWDOWN
            state["messages"].append(
                f"CRITICAL: Max Drawdown {state['max_drawdown']:.1%} breached limit {self.max_drawdown_limit:.1%}. FIRM FAILURE."
            )
            return state

        # Daily Stop Check (Assuming daily_pnl is absolute return, e.g. -0.025 for -2.5%)
        # If daily_pnl is dollars, we need to divide by NAV. Assuming state["daily_pnl"] is a percentage for simplicity now?
        # Let's assume daily_pnl is in DOLLARS in the state, so we divide by NAV.

        # Correction: State definition should be clear. Let's assume percentages for now or calculate.
        # Let's assume daily_pnl is raw PnL amount.
        daily_loss_pct = -state["daily_pnl"] / state["nav"] if state["nav"] > 0 else 0

        if state["daily_pnl"] < 0 and daily_loss_pct > self.daily_stop_limit:
            state["status"] = TradingStatus.SLEEPING
            state["messages"].append(
                f"RISK: Daily Loss {daily_loss_pct:.2%} exceeds limit {self.daily_stop_limit:.0%}. Sleeping logic activated."
            )
            return state

        # 2. Physics Veto Check
        # Check if the current regime (from State) is Critical
        if state.get("regime") == Regime.CRITICAL.value:
            state["status"] = TradingStatus.HALTED_PHYSICS
            state["messages"].append(
                f"PHYSICS VETO: Regime is {state['regime']} (Alpha {state.get('current_alpha', 'N/A')}). Trading Halted."
            )
            return state

        return state

    def update_physics(
        self, state: AgentState, historic_returns: np.ndarray
    ) -> AgentState:
        """
        Calculates Alpha and Updates Regime.
        """
        alpha = self.estimator.hill_estimator(historic_returns)
        regime_metrics = self.estimator.get_regime(alpha)

        state["current_alpha"] = alpha
        state["regime"] = regime_metrics.regime.value

        # Physics Veto Logic
        if regime_metrics.regime == Regime.CRITICAL:
            state["status"] = TradingStatus.HALTED_PHYSICS
            state["messages"].append(
                f"PHYSICS VETO: Alpha {alpha:.2f} indicates Critical Regime. Trading Halted."
            )

        return state

    def calculate_position_size(
        self, state: AgentState, es_returns: np.ndarray
    ) -> float:
        """
        Calculates position size using ES-Costrained Fractional Kelly.
        Size = (Equity * KellyFrac) / ES_95%
        """
        # Get leverage cap based on regime
        regime_metrics = self.estimator.get_regime(state["current_alpha"])
        if regime_metrics.leverage_cap == 0.0:
            return 0.0

        es_95 = expected_shortfall(es_returns, confidence_level=0.95)

        if es_95 == 0:
            return 0.0  # No risk data, no trade

        # Raw Size
        # Check standard Kelly limits? Here we use the simplified ES formula from the doc.
        # Ensure we don't divide by zero or negative ES (handled by positive return of expected_shortfall)

        size_dollars = (state["nav"] * self.kelly_fraction) / es_95

        # Apply Regime Cap
        # Effective leverage = Size / NAV
        # We need to clamp this. But the formula is for "Size" (likely dollars).
        # Let's check the leverage cap.

        max_position_dollars = state["nav"] * regime_metrics.leverage_cap

        final_size = min(size_dollars, max_position_dollars)

        return final_size


def risk_node(state: AgentState) -> AgentState:
    # This function creates a runnable node for the graph
    # Ideally checking external data for returns to update physics
    # For now, this is a placeholder stub for the graph integration
    manager = RiskManager()
    state = manager.check_governance(state)
    return state
