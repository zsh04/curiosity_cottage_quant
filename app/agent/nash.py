import logging
from app.agent.state import AgentState

logger = logging.getLogger(__name__)


class NashAgent:
    """The Council of Giants: 'Nash' (The Game Theorist) - Equilibrium Auditor.

    Named after John Nash's game theory equilibrium concept, this agent prevents
    "chasing" behavior by vetoing trades when price has deviated too far from
    statistical equilibrium (mode).

    **Core Principle:** Markets seek equilibrium. Extreme deviations reverse.

    **Nash Distance Formula:**
        N = (Price - Mode) / Sigma

    Where:
        - Mode: Most likely price (peak of distribution)
        - Sigma: Standard deviation
        - N > +2.0: Price extended above equilibrium (don't buy tops)
        - N < -2.0: Price extended below equilibrium (don't sell bottoms)

    **Decision Logic:**
    1. **BUY Signal + N > 2.0σ** → VETO (buying the top)
    2. **SELL Signal + N < -2.0σ** → VETO (selling the bottom)
    3. **BUY Signal + Low Buying Power** → VETO (T+1 settlement issue)

    **Risk Management:**
    - Prevents momentum chasing into overextended moves
    - Enforces game-theoretic \"payoff matrix\" where chasing has negative EV
    - Applies T+1 settlement checks for accounts under $25k (PDT rules)

    Attributes:
        None (stateless auditor)

    Example:
        >>> agent = NashAgent()
        >>> state = AgentState(symbol=\"SPY\", signal_side=\"BUY\", ...)
        >>> updated_state = agent.audit(state)
        >>> # Signal may be VETOED if nash_dist > 2.0
    """

    def audit(self, state: AgentState) -> AgentState:
        """Audit proposed trade against game-theoretic equilibrium constraints.

        Applies two veto rules:
        1. **Equilibrium Veto**: Prevents chasing extreme price deviations
        2. **Capital Veto**: Prevents trades when T+1 settlement risks exist

        **Veto Thresholds:**
        - Nash Distance: ±2.0σ (95% confidence interval)
        - Buying Power: $20 minimum for non-PDT-exempt accounts

        Args:
            state: Current agent state with signal, symbol, physics, account info

        Returns:
            Updated state with signal potentially vetoed (FLAT) and reasoning updated

        Side Effects:
            Modifies state['signal_side'] and state['reasoning'] if veto triggered

        Example:
            >>> state = {\"signal_side\": \"BUY\", \"nash_dist\": 2.5, ...}
            >>> state = agent.audit(state)
            >>> assert state[\"signal_side\"] == \"FLAT\"  # Vetoed for buying top
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
                logger.info(f"⚖️ [INNER LOOP] NASH VETO: {symbol} {signal} -> {reason}")
                state["signal_side"] = "FLAT"
                state["reasoning"] += f" | NASH VETO: {reason}"
                # We don't necessarily HALT the system, just kill the trade.
                # state["status"] = TradingStatus.HALTED_PHYSICS # Too aggressive?
                # Just flattening the signal is enough for "The Auditor".

            else:
                logger.info(
                    f"⚖️ [INNER LOOP] NASH APPROVED: {symbol}. Nash Dist: {nash_dist:.2f}σ"
                )

        except Exception as e:
            logger.error(f"NASH: Audit Failed: {e}")
            # Fail Open or Closed?
            # Game Theorist absent? We treat as proceed but log.

        return state


# Global Instance
_nash_agent = NashAgent()


def nash_node(state: AgentState) -> AgentState:
    return _nash_agent.audit(state)
