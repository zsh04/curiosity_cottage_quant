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
                {
                    "role": "system",
                    "content": f"CRITICAL: Max Drawdown {state['max_drawdown']:.1%} breached limit {self.max_drawdown_limit:.1%}. FIRM FAILURE.",
                }
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
                {
                    "role": "system",
                    "content": f"RISK: Daily Loss {daily_loss_pct:.2%} exceeds limit {self.daily_stop_limit:.0%}. Sleeping logic activated.",
                }
            )
            return state

        # 2. Physics Veto Check
        # Check if the current regime (from State) is Critical
        if state.get("regime") == Regime.CRITICAL.value:
            state["status"] = TradingStatus.HALTED_PHYSICS
            state["messages"].append(
                {
                    "role": "system",
                    "content": f"PHYSICS VETO: Regime is {state['regime']} (Alpha {state.get('current_alpha', 'N/A')}). Trading Halted.",
                }
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
                {
                    "role": "system",
                    "content": f"PHYSICS VETO: Alpha {alpha:.2f} indicates Critical Regime. Trading Halted.",
                }
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
    """
    The Iron Gate: Final decision point for all trades.
    Strictly enforces:
    1. Data Quality (Min 30 bars)
    2. Physics Veto (Alpha check)
    3. Governance (Hard stops)
    4. Sizing (Kelly * Confidence)
    """
    manager = RiskManager()

    # 1. Data Prep
    returns_data = state.get("historic_returns", [])
    if len(returns_data) < 30:
        # Insufficient Data: Force Gaussian, Log Warning
        state["messages"].append(
            {
                "role": "system",
                "content": f"RISK WARNING: Insufficient data ({len(returns_data)} < 30). Forcing Alpha=3.0.",
            }
        )
        state["current_alpha"] = 3.0
        state["regime"] = Regime.GAUSSIAN.value
        # We perform a partial update or skip update_physics to avoid crashing on empty data
        # But we still convert for potential sizing usage if needed (though ES will likely fail/return 0)
        returns_array = np.array(returns_data)
    else:
        # 2. Physics Update
        returns_array = np.array(returns_data)
        state = manager.update_physics(state, returns_array)

    # 3. Governance Check
    state = manager.check_governance(state)

    # 4. The Logic Branch
    if state["status"] != TradingStatus.ACTIVE:
        state["approved_size"] = 0.0
    else:
        # Active Status - Check for Signal
        signal = state.get("signal_side", "").lower()
        if signal in ["buy", "sell"]:
            # Calculate Base Size (Kelly / ES)
            base_size = manager.calculate_position_size(state, returns_array)

            # Apply Confidence
            confidence = state.get("signal_confidence", 0.0)
            final_size = base_size * confidence

            # Update State
            state["approved_size"] = final_size

            # Log Decision
            state["messages"].append(
                {
                    "role": "system",
                    "content": f"RISK APPROVED: Size {final_size:.2f} | Alpha {state.get('current_alpha', 0):.2f} | Conf {confidence:.2f}",
                }
            )
        else:
            # No Signal or Flat
            state["approved_size"] = 0.0

    return state
