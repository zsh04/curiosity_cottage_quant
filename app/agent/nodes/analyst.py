import logging
import asyncio
import time

from typing import Dict, Any
from opentelemetry import trace

from app.agent.state import AgentState
from app.services.market import MarketService
from app.services.physics import PhysicsService
from app.services.forecasting import ForecastingService
from app.services.reasoning import ReasoningService
from app.services.memory import MemoryService
from app.strategies.lstm import LSTMPredictionStrategy
from app.lib.physics import Regime
from app.services.global_state import (
    get_global_state_service,
    get_current_snapshot_id,
    save_model_checkpoint,
    load_latest_checkpoint,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AnalystAgent:
    """
    The Analyst Agent (Quant/Physics Hybrid).
    """

    def __init__(self):
        # Instantiate Services
        self.market = MarketService()
        self.physics = PhysicsService()
        self.forecasting = ForecastingService()
        self.reasoning = ReasoningService()
        self.memory = MemoryService()  # Quantum Memory

        # Strategy & Persistence
        self.lstm_model = LSTMPredictionStrategy()
        try:
            # TRY DB LOAD
            blob = load_latest_checkpoint("analyst_lstm")
            if blob:
                self.lstm_model.load_state_bytes(blob)
                logger.info("ANALYST: Loaded LSTM state from Database.")
            else:
                # FALLBACK TO FILE (Migration support)
                logger.info("ANALYST: No DB checkpoint found. Trying file...")
                self.lstm_model.load_state("data/models/lstm_analyst.pkl")

        except Exception as e:
            logger.warning(f"Failed to load LSTM state: {e}")

        self.cycle_count = 0

    async def _analyze_single(self, symbol: str) -> Dict[str, Any]:
        """
        Performs deep analysis on a single asset.
        Returns a dictionary of analysis results (Signal, Physics, Reasoning).
        """
        result_packet = {
            "symbol": symbol,
            "signal_side": "FLAT",
            "signal_confidence": 0.0,
            "reasoning": "",
            "velocity": 0.0,
            "regime": "Unknown",
            "hurst": 0.5,
            "success": False,
        }

        try:
            # --- PHASE 0: WARM-UP (If needed) ---
            # Ideally, we warm up once per symbol or system start.
            # We track this locally or via Physics Service which is stateful.
            # If PhysicsService says not initialized, we warm up.
            if not self.physics.is_initialized:
                startup_bars = await asyncio.to_thread(
                    self.market.get_startup_bars, symbol, limit=100
                )
                # Warmup Physics
                await asyncio.to_thread(self.physics.calculate_kinematics, startup_bars)

                # Warmup/Init LSTM (feed returns)
                # LSTM expects DataFrame usually or raw prices.
                # Let's verify calculate_signal signature: expects DataFrame with "close".
                import pandas as pd

                if startup_bars:
                    df_warmup = pd.DataFrame({"close": startup_bars})
                    # We just call calculate_signal which handles warmup internally if uninitialized
                    self.lstm_model.calculate_signal(df_warmup)
                    logger.info(f"🔥 ANALYST: Warm-up complete for {symbol}")

            # --- Step 1: SENSES (Market Data) ---
            market_snapshot = await asyncio.to_thread(
                self.market.get_market_snapshot, symbol
            )

            # Extract basics
            history = market_snapshot.get("history", [])

            # --- Step 2: PHYSICS (Kinematics & Regime) ---
            kinematics = await asyncio.to_thread(
                self.physics.calculate_kinematics, history
            )
            regime_analysis = await asyncio.to_thread(
                self.physics.analyze_regime, history
            )
            hurst_analysis = await asyncio.to_thread(
                self.physics.calculate_hurst_and_mode, history
            )
            qho_analysis = await asyncio.to_thread(
                self.physics.calculate_qho_levels, history
            )

            physics_context = {
                **kinematics,
                **regime_analysis,
                **hurst_analysis,
                **qho_analysis,
            }

            # --- Step 2.5: STRATEGY (LSTM Model) ---
            # Update/Predict with latest data
            lstm_signal = 0.0
            if history:
                import pandas as pd

                df_latest = pd.DataFrame({"close": history})
                lstm_signal = self.lstm_model.calculate_signal(df_latest)

            # Persistence Check
            self.cycle_count += 1
            if self.cycle_count % 100 == 0:
                # Save to DB
                blob = self.lstm_model.get_state_bytes()
                if blob:
                    # This runs in main thread, which blocks, but saving byte checkoint to DB is fast usually
                    # To avoid blocking, we could run in executor, but sqlalchemy session is not thread-safe usually
                    # unless scoped. For now, running sync is safer for integrity.
                    await asyncio.to_thread(save_model_checkpoint, "analyst_lstm", blob)
                    logger.info("💾 ANALYST: Saved LSTM checkpoint to Database.")

            # --- Step 3: FUTURE (Forecasting) ---
            forecast = await asyncio.to_thread(
                self.forecasting.predict_trend, history, 10
            )

            # --- Step 3.5: MEMORY (Quantum Recall) ---
            sentiment_snapshot = market_snapshot.get("sentiment", {})
            historical_regimes = await asyncio.to_thread(
                self.memory.retrieve_similar,
                symbol,
                physics_context,
                sentiment_snapshot,
                k=3,
            )
            market_snapshot["historical_regimes"] = historical_regimes

            # --- Step 4: COGNITION (Reasoning / Signal) ---
            reasoning_context = {
                "market": market_snapshot,
                "physics": physics_context,
                "forecast": forecast,
                "sentiment": sentiment_snapshot,
                "strategies": {"lstm_signal": lstm_signal},  # Inject LSTM signal
            }

            signal_result = await asyncio.to_thread(
                self.reasoning.generate_signal, reasoning_context
            )

            # --- Step 5.5: MEMORIZE (Fire & Forget) ---
            asyncio.create_task(
                asyncio.to_thread(
                    self.memory.save_regime, symbol, physics_context, sentiment_snapshot
                )
            )

            # Populate Result Packet
            result_packet.update(
                {
                    "signal_side": signal_result.get("signal_side", "FLAT"),
                    "signal_confidence": signal_result.get("signal_confidence", 0.0),
                    "reasoning": signal_result.get("reasoning", ""),
                    "velocity": kinematics["velocity"],
                    "acceleration": kinematics["acceleration"],
                    "regime": regime_analysis["regime"],
                    "current_alpha": regime_analysis["alpha"],
                    "hurst": hurst_analysis["hurst"],
                    "strategy_mode": hurst_analysis["strategy_mode"],
                    "price": market_snapshot.get("price", 0.0),
                    "history": history,  # Careful with size, but needed for state
                    "success": True,
                }
            )

            return result_packet

        except Exception as e:
            logger.error(f"ANALYST: Single Analysis Failed for {symbol}: {e}")
            result_packet["reasoning"] = f"CRASH: {e}"
            return result_packet

    async def analyze(self, state: AgentState) -> AgentState:
        """
        Quantum Batch Analysis.
        1. Inspects 'watchlist' (from Parallel Field Scanner) or 'candidates'.
        2. Spawns '_analyze_single' for each candidate in parallel.
        3. Collapses Wavefunction: Selects the highest confidence signal.
        4. Stores full superposition state in 'analysis_reports'.
        """
        # Phase 16: Priority to Watchlist (from Macro Node)
        candidates = state.get("watchlist", [])
        if not candidates:
            candidates = state.get("candidates", [])

        # Fallback: If no batch, analyze the single symbol provided in state
        if not candidates:
            target_symbol = state.get("symbol", "SPY")
            logger.warning(
                f"ANALYST: No candidates found. Fallback to single symbol: {target_symbol}"
            )
            candidates = [{"symbol": target_symbol}]

        symbols = [c["symbol"] for c in candidates]
        logger.info(
            f"🧠 ANALYST: Starting Batch Analysis for {len(symbols)} assets: {symbols}"
        )

        start_time = time.time()

        # --- PARALLEL EXECUTION ---
        tasks = [self._analyze_single(sym) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge Results
        enriched_candidates = []
        for i, res in enumerate(results):
            # Candidate dict from input (watchlist item)
            candidate = candidates[i].copy()

            if isinstance(res, dict):
                # Update with analysis results
                candidate.update(res)
            else:
                candidate["error"] = str(res)
                candidate["signal_confidence"] = -1.0
                logger.error(
                    f"ANALYST: Analysis failed for {candidate.get('symbol')}: {res}"
                )

            enriched_candidates.append(candidate)

        # --- SUPERPOSITION OUTPUT ---
        # Store full reports for downstream reasoning/risk
        state["analysis_reports"] = enriched_candidates
        state["candidates"] = enriched_candidates  # Backwards compatibility

        # --- SELECTION Logic (Wavefunction Collapse) ---
        # Sort by Confidence Descending
        enriched_candidates.sort(
            key=lambda x: x.get("signal_confidence", 0.0), reverse=True
        )

        winner = None

        # Resilient Collapse: Iterate to find first non-critical candidate
        for candidate in enriched_candidates:
            alpha = candidate.get("current_alpha", 2.0)
            regime = candidate.get("regime", "Unknown")

            # The "Iron Gate" Check (Self-Imposed by Analyst)
            # We reject candidates in Infinite Variance regimes to prevent Risk Node Halt
            if alpha <= 2.0 or regime == Regime.CRITICAL.value:
                logger.warning(
                    f"ANALYST: Vetoed candidate {candidate['symbol']} (Alpha: {alpha:.2f}, Regime: {regime}). "
                    f"Conf: {candidate.get('signal_confidence', 0):.2f}"
                )
                continue

            # If passed, we found our winner
            winner = candidate
            break

        # Fallback: If ALL candidates are Critical (Market Crash), pick the top one but force FLAT?
        # Or pick the safest one?
        # For now, if no winner, we revert to the top candidate but warn heavily,
        # knowing Risk might halt us. Better to be halted than trade critical.
        if not winner:
            logger.warning(
                "ANALYST: ⚠️ ALL candidates failed Physics Veto. Collapse forced to Top Candidate (Risk of Halt)."
            )
            winner = enriched_candidates[0]

        logger.info(
            f"ANALYST: 🏆 Winner Selected: {winner['symbol']} (Conf: {winner.get('signal_confidence', 0):.2f})"
        )

        # Update Top-Level State (The collapsed reality for Execution)
        state["symbol"] = winner["symbol"]
        state["signal_side"] = winner.get("signal_side", "FLAT")
        state["signal_confidence"] = winner.get("signal_confidence", 0.0)
        state["reasoning"] = winner.get("reasoning", "")
        state["price"] = winner.get("price", 0.0)

        state["velocity"] = winner.get("velocity", 0.0)
        state["acceleration"] = winner.get("acceleration", 0.0)
        state["regime"] = winner.get("regime", "Unknown")
        state["current_alpha"] = winner.get("current_alpha", 2.0)
        state["hurst"] = winner.get("hurst", 0.5)
        state["strategy_mode"] = winner.get("strategy_mode", "Unknown")

        # Also store the raw history if available, for Execution constraints?
        if "history" in winner:
            state["history"] = winner["history"]

        # Telemetry
        latency = (time.time() - start_time) * 1000
        self._log_telemetry(winner, latency, success=True)

        return state

    def _log_telemetry(self, data: dict, latency_ms: float, success: bool):
        # Helper to log metrics to global state
        try:
            state_service = get_global_state_service()
            snapshot_id = get_current_snapshot_id()

            if state_service and snapshot_id:
                state_service.save_agent_metrics(
                    snapshot_id=snapshot_id,
                    agent_name="analyst",
                    latency_ms=latency_ms,
                    success=success,
                    output_data={
                        "symbol": data.get("symbol"),
                        "signal_side": data.get("signal_side"),
                        "confidence": data.get("signal_confidence"),
                        "reasoning": data.get("reasoning"),
                    },
                    error=None,
                )
        except Exception as e:
            logger.error(f"Failed to log telemetry: {e}")


def analyst_node(state: AgentState) -> AgentState:
    """
    LangGraph Node Wrapper (Synchronous).
    """
    agent = AnalystAgent()
    return asyncio.run(agent.analyze(state))
