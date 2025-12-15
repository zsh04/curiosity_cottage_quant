from app.agent.state import AgentState


class RiskAgent:
    """
    The 'Guardian' agent.
    Responsibility: Prevent ruin.
    Authority: Absolute Veto power over Execution.
    """

    @staticmethod
    def physics_veto(state: AgentState) -> AgentState:
        """
        Node function to apply physics-based risk constraints.
        """
        print("--- RISK AGENT: Checking Constraints ---")

        regime = state.get("regime", "GAUSSIAN")
        current_decision = state.get("trade_decision", "HOLD")

        # 1. The Alpha Veto
        # If the market is in a Levy Stable regime (Infinite Variance),
        # standard predictive models fail. We must VETO unless strategy is specifically tail-convex.
        # For this version, we VETO all directional trades in High Volatility.
        if regime in ["LEVY", "CAUCHY"]:
            print(f"!!! RISK VETO TRIGGERED: Regime is {regime} !!!")
            return {"trade_decision": "VETO_PHYSICS", "risk_score": 100.0}

        print("Risk Check Passed. Regime is Gaussian.")
        return {
            "risk_score": 0.0
            # We do not overwrite 'trade_decision' if passing, we leave it as is
            # (or receiving node handles it)
        }
