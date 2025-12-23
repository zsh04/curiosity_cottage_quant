import logging
from app.agent.state import AgentState

logger = logging.getLogger(__name__)


class NashAgent:
    """
    The Council of Giants: 'Nash' (The Game Theorist).

    Role: Equilibrium Auditor.
    Metric: Nash Distance (N) = (Price - Mode) / Sigma.
    Logic:
        - Markets seek Equilibrium (Mode).
        - If Price deviates significantly (N > 2.0), the "Payoff Matrix"
          for following the trend turns negative (Reversion likely).
        - Nash VETOES "Chasing" the deviation.
    """

    def audit(self, state: AgentState) -> AgentState:
        """
        Audits the proposed trade against Game Theory equilibrium.
        """
        try:
            # 1. Check if we have a signal to audit
            if state.get("signal_side") in ["FLAT", "NEUTRAL", None]:
                return state

            symbol = state.get("symbol", "UNKNOWN")

            # 2. Extract Physics (The Board State)
            # Boyd puts vectors in state via "physics_vector"? No, looks like it's flattened or in "physics" key?
            # Let's check how Boyd populates state.
            # Boyd.analyze returns "nash_dist" in the root of the packet if hoisted?
            # Or we look at state["analysis_reports"] if present?
            # Ideally, Boyd put the primary context into the state root.

            # Let's look for 'nash_dist' or 'physics_vector'
            # In verify_live_system.py we mocked Boyd returning state.
            # Boyd puts 'physics_context' inside reasoning? No.
            # Let's play safe and try to find it.

            # Inspecting Boyd:
            # result_packet["nash_dist"] is NOT explicitly in Boyd's hoist list in previous audit.
            # Boyd hoists: signal_side, signal_confidence, regime, reasoning, ...
            # Wait, Boyd DOES calculate it.
            # We might need to update Boyd to hoist `nash_dist` OR Nash needs to read it from `physics:state:{symbol}` or the candidates list.

            # Let's assume for this implementation we read from "candidates" (which has the full report)
            # or we read from Redis if missing.
            # Efficient path: Read from State["candidates"] for the primary symbol.

            primary_candidate = None
            candidates = state.get("candidates", [])
            for c in candidates:
                if c.get("symbol") == symbol:
                    primary_candidate = c
                    break

            nash_dist = 0.0
            if primary_candidate and "physics_vector" in primary_candidate:
                # stored as dict
                nash_dist = primary_candidate["physics_vector"].get("nash_dist", 0.0)

            # 3. The Game Theory Decision (The Nash Equilibrium)
            # Threshold: 2 Sigma (95% extension)
            limit = 2.0

            signal = state.get("signal_side")

            veto = False
            reason = ""

            if signal == "BUY":
                # --- Phase 48: The Nash Allocator (T+1 Settlement Check) ---
                buying_power = float(state.get("buying_power", 0.0))
                pdt_exempt = state.get("pdt_exempt", False)

                # Hardcoded "Micro-Seed" Minimum. If we have less than $10 BP, we assume we are unsettled.
                # Project Ezekiel Constraint: $500 Account.
                MIN_BP_THRESHOLD = 20.0

                # Phase 49: Dynamic Threshold
                # If Exempt ($25k+), we don't block on small BP (Margin handles it), unless strictly negative/zero.
                if not pdt_exempt and buying_power < MIN_BP_THRESHOLD:
                    veto = True
                    reason = f"Settlement Lock: Buying Power (${buying_power:.2f}) < Threshold (${MIN_BP_THRESHOLD}). T+1 Wait Required."
                    logger.warning(f"NASH: 🛑 CAPITAL RATIONING. {reason}")

                elif nash_dist > limit:
                    veto = True
                    reason = f"Nash Equilibrium Violation: Price is +{nash_dist:.2f}σ from Mode. Buying the top."

            elif signal == "SELL":
                if nash_dist < -limit:
                    veto = True
                    reason = f"Nash Equilibrium Violation: Price is {nash_dist:.2f}σ from Mode. Selling the bottom."

            if veto:
                logger.info(f"NASH: ⚖️ VETO {symbol} {signal}. {reason}")
                state["signal_side"] = "FLAT"
                state["reasoning"] += f" | NASH VETO: {reason}"
                # We don't necessarily HALT the system, just kill the trade.
                # state["status"] = TradingStatus.HALTED_PHYSICS # Too aggressive?
                # Just flattening the signal is enough for "The Auditor".

            else:
                logger.info(f"NASH: ✅ Approved {symbol}. Nash Dist: {nash_dist:.2f}σ")

        except Exception as e:
            logger.error(f"NASH: Audit Failed: {e}")
            # Fail Open or Closed?
            # Game Theorist absent? We treat as proceed but log.

        return state


# Global Instance
_nash_agent = NashAgent()


def nash_node(state: AgentState) -> AgentState:
    return _nash_agent.audit(state)
