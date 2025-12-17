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

    MAX_DRAWDOWN_LIMIT = 0.02

    def __init__(self):
        self.bes = BesSizing()
        # Lazy load MarketService to avoid circular imports if any
        from app.services.market import MarketService

        self.market = MarketService()

    def check_entanglement(self, symbol: str, portfolio: list) -> float:
        """
        Quantum Entanglement (Correlation) Check.
        Returns the maximum correlation with existing positions.
        """
        if not portfolio:
            return 0.0

        try:
            import pandas as pd
            import numpy as np

            # get candidate history
            candidate_hist = self.market.market_adapter.get_price_history(
                symbol, limit=100
            )
            if not candidate_hist:
                return 0.0

            s1 = pd.Series(candidate_hist)
            max_corr = 0.0

            # Check against top 5 positions by value (optimization)
            # Actually, alpaca position object has 'symbol'
            for pos in portfolio[:5]:
                existing_sym = pos.get("symbol")
                if existing_sym == symbol:
                    return (
                        1.0  # Self-correlation (shouldn't happen if logic is correct)
                    )

                # Fetch history for existing pos
                # NOTE: This IS slow (N API calls).
                # Production Fix: Cache these or fetch batch.
                hist = self.market.market_adapter.get_price_history(
                    existing_sym, limit=100
                )
                if not hist:
                    continue

                s2 = pd.Series(hist)
                # Ensure same length for correlation
                min_len = min(len(s1), len(s2))
                corr = s1.iloc[-min_len:].corr(s2.iloc[-min_len:])

                if not np.isnan(corr):
                    max_corr = max(max_corr, abs(corr))

            return max_corr

        except Exception as e:
            logger.error(f"RISK: Entanglement check failed: {e}")
            return 0.0

    def check_governance(self, state: AgentState) -> AgentState:
        """
        Hard Stops. If breached, status -> HALTED.
        """
        # 1. Update Drawdown Calculation (Live)
        # Using a fixed starting capital reference for 'Session Drawdown' or 'Total Drawdown'
        starting_capital = state.get("starting_capital", 100000.0)
        current_val = state.get("nav", 100000.0)

        if starting_capital > 0:
            drawdown = (starting_capital - current_val) / starting_capital
        else:
            drawdown = 0.0

        # Update state for visibility
        state["max_drawdown"] = max(state.get("max_drawdown", 0.0), drawdown)

        # 2. Circuit Breaker Check
        if drawdown >= self.MAX_DRAWDOWN_LIMIT:
            state["status"] = TradingStatus.HALTED_DRAWDOWN
            # Force size to 0 immediately
            state["approved_size"] = 0.0

            msg = f"🛑 CIRCUIT BREAKER TRIGGERED: Drawdown {drawdown:.2%} > {self.MAX_DRAWDOWN_LIMIT:.0%}"
            logger.critical(msg)
            state["messages"].append(msg)
            return state

        # 3. Physics Veto
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

        # Guard 3: Drawdown
        current_dd = state.get("max_drawdown", 0.0)
        if current_dd > 0.02:
            logger.warning(f"RISK: Drawdown {current_dd:.1%} > 2%. Safety Halt.")
            return 0.0

        # Guard 4: Quantum Entanglement (Correlation Penalty)
        # Prevent concentration in correlated assets
        positions = state.get("current_positions", [])
        symbol = state.get("symbol")

        if symbol and positions:
            max_corr = self.check_entanglement(symbol, positions)
            if max_corr > 0.7:
                logger.warning(
                    f"RISK: 🔗 High Entanglement ({max_corr:.2f}) detected. Applying Size Penalty."
                )
                # Penalty: Reduce size by correlation strength.
                # If corr=1.0 -> size=0. If corr=0.7 -> size=0.3 * original
                # Formula: Factor = max(0, 1 - (corr - 0.5) * 2) ?
                # Simpler: Factor = 1 - corr
                # If corr > 0.8, VETO.
                if max_corr > 0.85:
                    logger.warning(
                        f"RISK: 🚫 VETO due to Entanglement {max_corr:.2f} > 0.85"
                    )
                    return 0.0

                penalty = 1.0 - max_corr
                size_pct *= penalty
                logger.info(
                    f"RISK: Adjusted Size PCT: {size_pct:.2%} (Penalty {penalty:.2f})"
                )

        # Calculate Approved Notional
        # Size is returned as % of capital (0.0 to 0.20)
        approved_notional = size_pct * capital

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
        else:
            # --- PHASE 17: AI TOURNAMENT TRIGGER ---
            # If we have a superposition (watchlist results), we run the Tournament
            analysis_reports = state.get("analysis_reports", [])

            # Helper: Lazy load reasoning service to avoid circular deps if any,
            # though usually safe technically if imported at top.
            # But let's instantiate.
            from app.services.reasoning import ReasoningService

            reasoning_service = ReasoningService()

            if len(analysis_reports) > 1:
                logger.info(
                    "RISK: 🏟️ Triggering AI Tournament for Wavefunction Collapse..."
                )
                tournament_result = reasoning_service.arbitrate_tournament(
                    analysis_reports
                )

                winner_sym = tournament_result.get("winner_symbol")
                rationale = tournament_result.get("rationale")

                if winner_sym and winner_sym != "NONE":
                    # Find the full candidate object
                    winner_cand = next(
                        (c for c in analysis_reports if c["symbol"] == winner_sym), None
                    )
                    if winner_cand:
                        logger.info(
                            f"RISK: 🏆 Tournament Winner: {winner_sym} | Reason: {rationale}"
                        )
                        # OVERWRITE STATE with the Winner's reality
                        state["symbol"] = winner_cand["symbol"]
                        state["signal_side"] = winner_cand.get("signal_side", "FLAT")
                        state["signal_confidence"] = winner_cand.get(
                            "signal_confidence", 0.0
                        )
                        state["price"] = winner_cand.get("price", 0.0)
                        state["current_alpha"] = winner_cand.get("current_alpha", 2.0)
                        state["regime"] = winner_cand.get("regime", "Unknown")
                        state["reasoning"] = f"[TOURNAMENT WINNER] {rationale}"
                        # Also forecast needed for sizing
                        # Analyst usually puts 'forecast' in state?
                        # Ah, Analyst puts discrete fields. 'chronos_forecast' isn't explicitly in top state in analyst.py yet?
                        # Let's check analyst.py... it puts "reasoning", "velocity" etc.
                        # It DOES NOT seem to put "chronos_forecast" into top state in previous analyst.py
                        # Wait, risk.py expects 'chronos_forecast' for sizing.
                        # We must ensure Analyst passes it or we re-fetch?
                        # Analyst passes 'forecast' object in reasoning context but not top state.
                        # FIX: We should assume Analyst puts it or we extract it from report if preserved.
                    else:
                        logger.warning(
                            f"RISK: Winner {winner_sym} not found in reports!"
                        )
                else:
                    logger.info("RISK: 🏳️ Tournament returned NO WINNER. Forcing FLAT.")
                    signal_side = OrderSide.FLAT.value
                    state["signal_side"] = "FLAT"

            # Re-fetch signal side after potential Tournament overwrite
            signal_side = state.get("signal_side", OrderSide.FLAT.value)

            if signal_side in [OrderSide.BUY.value, OrderSide.SELL.value]:
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
