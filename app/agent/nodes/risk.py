import logging
import time
from typing import Optional
from app.agent.state import AgentState, TradingStatus, OrderSide
from app.lib.physics import Regime
from app.agent.risk.bes import BesSizing
from app.core import metrics as business_metrics
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

    def check_circuit_breaker(self, state: AgentState) -> AgentState:
        """
        Hard Stops: Global Circuit Breaker (Drawdown).
        This runs BEFORE any analysis or tournament.
        """
        # 1. Update Drawdown Calculation (Live)
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
            state["approved_size"] = 0.0

            msg = f"🛑 CIRCUIT BREAKER TRIGGERED: Drawdown {drawdown:.2%} > {self.MAX_DRAWDOWN_LIMIT:.0%}"
            logger.critical(msg)
            business_metrics.vetoes_total.add(1, {"reason": "drawdown"})  # Metric
            return state

        # If OK, keep status unless already halted
        if state.get("status") in [
            TradingStatus.HALTED_DRAWDOWN,
            TradingStatus.HALTED_PHYSICS,
        ]:
            # Don't auto-reset if halted previously without manual intervention?
            # For now, we assume simple state: if DD is ok, we are ACTIVE unless physics veto later.
            pass
        else:
            state["status"] = TradingStatus.ACTIVE

        return state

    def check_physics_veto(self, state: AgentState) -> AgentState:
        """
        Physics Veto: Symbol-Specific Regime Check.
        This runs AFTER the Tournament winner is selected.
        """
        regime = state.get("regime", "Unknown")

        # Check Critical Regime
        if regime == Regime.CRITICAL.value:
            state["status"] = TradingStatus.HALTED_PHYSICS
            state["approved_size"] = 0.0
            msg = f"PHYSICS VETO: Critical Regime detected for {state.get('symbol')}. Trading Halted."
            logger.warning(msg)
            business_metrics.vetoes_total.add(
                1, {"reason": "critical_regime"}
            )  # Metric
            return state

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

    # Ensure messages list exists
    if "messages" not in state:
        state["messages"] = []

    try:
        # --- STEP 1: GLOBAL CIRCUIT BREAKER ---
        # Checks Drawdown / Account Health independent of any symbol
        state = manager.check_circuit_breaker(state)

        if state.get("status") == TradingStatus.HALTED_DRAWDOWN:
            # Global Halt - Abort immediately
            return state

        # --- STEP 2: TOURNAMENT OF MINDS (Selection) ---
        # The Analyst provided a list of reports. Risk decides the winner.

        analysis_reports = state.get("analysis_reports", [])
        winner_cand = None
        rationale = "Default"

        if not analysis_reports:
            logger.warning("RISK: No analysis reports available for tournament.")
            state["signal_side"] = "FLAT"
            state["approved_size"] = 0.0
            return state

        # Setup Reasoning Service
        from app.services.reasoning import get_reasoning_service

        reasoning_service = get_reasoning_service()

        # A. Check Asynchronous Background Brain Result (Priority)
        bg_result = reasoning_service.check_background_result()
        if bg_result and bg_result.get("winner_symbol") not in [None, "NONE"]:
            winner_sym = bg_result.get("winner_symbol")
            winner_cand = next(
                (r for r in analysis_reports if r["symbol"] == winner_sym), None
            )
            if winner_cand:
                rationale = (
                    f"[BACKGROUND] {bg_result.get('rationale', 'Async Decision')}"
                )
                logger.info(f"RISK: 🧠 Valid Background Brain Decision: {winner_sym}")

        # B. Run Live Tournament (if no bg result)
        if not winner_cand:
            if len(analysis_reports) > 1:
                # Multi-Candidate: Invoke Cloud Tournament
                logger.info(
                    f"RISK: 🏟️ Starting Tournament for {len(analysis_reports)} candidates..."
                )
                try:
                    arb_result = reasoning_service.arbitrate_tournament(
                        analysis_reports
                    )
                    winner_sym = arb_result.get("winner_symbol")
                    if winner_sym and winner_sym != "NONE":
                        winner_cand = next(
                            (r for r in analysis_reports if r["symbol"] == winner_sym),
                            None,
                        )
                        if winner_cand:
                            rationale = f"AI Decision: {arb_result.get('rationale')}"
                        else:
                            logger.warning(
                                f"RISK: AI selected {winner_sym} but it's not in current reports."
                            )
                    else:
                        # AI explicitly selected NONE. Use its rationale.
                        rationale = f"AI Veto: {arb_result.get('rationale', 'Safety/No Confluence')}"
                except Exception as e:
                    logger.error(f"RISK: Tournament Error: {e}")
                    # Fallback: Submit to background? Or pick best confident?
                    # For now: Fallback to highest confidence

            elif len(analysis_reports) == 1:
                # Single Candidate: Auto-Select
                winner_cand = analysis_reports[0]
                rationale = "Single Candidate Logic"

        # --- STEP 3: COLLAPSE WAVEFUNCTION (Update State) ---
        if winner_cand:
            state["symbol"] = winner_cand["symbol"]
            state["price"] = winner_cand.get("price", 0.0)
            state["velocity"] = winner_cand.get("velocity", 0.0)
            state["acceleration"] = winner_cand.get("acceleration", 0.0)
            state["current_alpha"] = winner_cand.get("current_alpha", 2.0)
            state["regime"] = winner_cand.get("regime", "Unknown")
            state["signal_side"] = winner_cand.get("signal_side", "FLAT")
            state["signal_confidence"] = winner_cand.get("signal_confidence", 0.0)
            state["reasoning"] = f"{rationale} | {winner_cand.get('reasoning')}"

            logger.info(
                f"🏆 RISK WINNER: {state['symbol']} ({state['signal_side']}) | Vel={state['velocity']:.4f}"
            )

            # Telemetry: Physics State
            business_metrics.alpha_tail.set(
                state["current_alpha"],
                {"symbol": state["symbol"], "regime": state["regime"]},
            )
            business_metrics.velocity.set(
                state["velocity"], {"symbol": state["symbol"]}
            )
            business_metrics.acceleration.set(
                state["acceleration"], {"symbol": state["symbol"]}
            )

        else:
            state["signal_side"] = "FLAT"
            state["approved_size"] = 0.0
            state["reasoning"] = f"RISK: No Winner Selected ({rationale})"
            logger.info("RISK: No Winner. Flat.")
            return state

        # --- STEP 4: PHYSICS VETO (Symbol Specific) ---
        # Now that we have a symbol and regime, check logic stops
        state = manager.check_physics_veto(state)

        if state.get("status") == TradingStatus.HALTED_PHYSICS:
            return state

        # --- STEP 5: SIZING ---
        # If Active and Side is actionable, calculate size
        signal_side = state.get("signal_side", "FLAT")
        if signal_side in ["BUY", "SELL"]:
            size_notional = manager.size_position(state)
            state["approved_size"] = size_notional

            # Telemetry: Position Size
            business_metrics.position_size.set(
                size_notional, {"symbol": state["symbol"], "side": signal_side}
            )

            # Logging
            alpha_val = state.get("current_alpha", 0.0)
            size_pct = size_notional / state.get("nav", 100000.0)

            # Message
            msg = f"⚖️ SIZING ({state['symbol']}): Alpha={alpha_val:.2f} | Size={size_pct:.2%} (${size_notional:.0f})"
            state["messages"].append(msg)
            logger.info(msg)
        else:
            state["approved_size"] = 0.0

    except Exception as e:
        success = False
        error_msg = f"RISK: 💥 CRASH: {e}"
        logger.exception(error_msg)
        state["approved_size"] = 0.0
        state["messages"].append(error_msg)
        business_metrics.vetoes_total.add(1, {"reason": "crash"})

    finally:
        # TELEMETRY
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
