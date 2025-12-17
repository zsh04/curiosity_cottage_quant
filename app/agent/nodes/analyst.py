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
        # self.physics = PhysicsService()  # REMOVED: Shared instance causes bleed
        self.physics_map: Dict[str, PhysicsService] = {}  # NEW: Per-symbol factory
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

    def _get_physics_service(self, symbol: str) -> PhysicsService:
        """
        Factory method to get or create a unique PhysicsService for a symbol.
        Ensures strict state isolation (Kalman Filter, Velocity, etc.)
        """
        if symbol not in self.physics_map:
            logger.info(f"ANALYST: 🏭 Spawning new Physics Engine for {symbol}")
            self.physics_map[symbol] = PhysicsService()
        return self.physics_map[symbol]

    async def _analyze_single(
        self, symbol: str, skip_llm: bool = False
    ) -> Dict[str, Any]:
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
        logger.info(f"DEBUG: Analyzing {symbol} with skip_llm={skip_llm}")

        try:
            # Get Isolated Physics Engine
            physics_engine = self._get_physics_service(symbol)

            # --- PHASE 0: WARM-UP (If needed) ---
            # Ideally, we warm up once per symbol or system start.
            # We track this locally or via Physics Service which is stateful.
            # If PhysicsService says not initialized, we warm up.
            if not physics_engine.is_initialized:
                startup_bars = await asyncio.to_thread(
                    self.market.get_startup_bars, symbol, limit=100
                )
                # Warmup Physics
                await asyncio.to_thread(
                    physics_engine.calculate_kinematics, startup_bars
                )

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
            current_price = market_snapshot.get("price", 0.0)
            logger.info(
                f"Checking Data {symbol}: Price={current_price} Hist={len(history)}"
            )

            # --- DYNAMIC PHYSICS INJECTION ---
            # Append live price as the latest "tick" to force non-zero velocity calculation
            # relative to the previous close.
            physics_history = history.copy()
            if current_price > 0:
                physics_history.append(current_price)

            # --- Step 2: PHYSICS (Kinematics & Regime) ---
            kinematics = await asyncio.to_thread(
                physics_engine.calculate_kinematics, physics_history
            )
            logger.info(f"DEBUG: {symbol} Raw Velocity: {kinematics.get('velocity')}")
            regime_analysis = await asyncio.to_thread(
                physics_engine.analyze_regime, physics_history
            )
            hurst_analysis = await asyncio.to_thread(
                physics_engine.calculate_hurst_and_mode, physics_history
            )
            qho_analysis = await asyncio.to_thread(
                physics_engine.calculate_qho_levels, physics_history
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
            if not skip_llm:
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
            else:
                # OPTIMIZATION: Skip LLM for non-primary candidates
                signal_result = {
                    "signal_side": "FLAT",
                    "signal_confidence": 0.0,
                    "reasoning": "LLM Skipped (Optimization)",
                }
                # Basic LSTM fallback for signal side
                if lstm_signal > 0.05:
                    signal_result["signal_side"] = "BUY"
                    signal_result["signal_confidence"] = min(abs(lstm_signal) * 5, 0.8)
                elif lstm_signal < -0.05:
                    signal_result["signal_side"] = "SELL"
                    signal_result["signal_confidence"] = min(abs(lstm_signal) * 5, 0.8)

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

        # Ensure Primary Symbol (from Loop/UI) is ALWAYS included in analysis
        # Otherwise we broadcast stale data (Vel=0.0) for the active symbol.
        target_symbol = state.get("symbol", "SPY")
        primary_in_batch = any(c.get("symbol") == target_symbol for c in candidates)

        if not primary_in_batch:
            # Inject at top priority
            candidates.insert(0, {"symbol": target_symbol})

        if not candidates:
            # Fallback if watchlist and symbol were both empty (rare)
            logger.warning(
                f"ANALYST: No candidates found. Fallback to single symbol: {target_symbol}"
            )
            candidates = [{"symbol": target_symbol}]

        symbols = [c["symbol"] for c in candidates]
        primary_symbol = state.get("symbol", "SPY")
        tasks = []

        # --- PARALLEL EXECUTION (Conditional LLM) ---
        # Phase 27: Optimization - Only use LLM for Primary Symbol to prevent local LLM overload.
        # Secondary symbols get LSTM/Tech signals only.
        for candidate_item in candidates:
            symbol = candidate_item["symbol"]
            is_primary = symbol == primary_symbol
            should_skip_llm = not is_primary

            tasks.append(self._analyze_single(symbol, skip_llm=should_skip_llm))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # --- MERGE & HOIST ---
        enriched_candidates = []
        primary_data = None

        for i, res in enumerate(results):
            # Candidate dict from input
            candidate = candidates[i].copy()

            if isinstance(res, dict):
                candidate.update(res)
                # Check match
                if candidate.get("symbol") == primary_symbol:
                    primary_data = candidate
            elif isinstance(res, Exception):
                logger.error(
                    f"ANALYST: Error analyzing {candidate.get('symbol')}: {res}"
                )
                candidate["error"] = str(res)
                candidate["success"] = False

            enriched_candidates.append(candidate)

        # Update State
        state["analysis_reports"] = enriched_candidates
        state["candidates"] = enriched_candidates  # Backwards compatibility

        # Hoist Primary Data to Top Level
        if primary_data:
            state["price"] = primary_data.get("price", 0.0)
            state["velocity"] = primary_data.get("velocity", 0.0)
            state["acceleration"] = primary_data.get("acceleration", 0.0)
            state["current_alpha"] = primary_data.get("current_alpha", 2.0)
            state["regime"] = primary_data.get("regime", "Unknown")
            state["signal_side"] = primary_data.get("signal_side", "FLAT")
            state["signal_confidence"] = primary_data.get("signal_confidence", 0.0)
            state["reasoning"] = primary_data.get("reasoning", "Analysis Complete")
            state["history"] = primary_data.get("history", [])
            logger.info(f"✅ ANALYST: Hoisted {primary_symbol} Price=${state['price']}")
        else:
            logger.warning(
                f"⚠️ ANALYST: Primary symbol {primary_symbol} not in batch results."
            )

        # LOGGING (Batch Summary)
        successful = [c for c in enriched_candidates if c.get("success")]
        logger.info(
            f"ANALYST: Batch Analysis Complete. {len(successful)}/{len(enriched_candidates)} successful."
        )

        # Telemetry (Metrics for Batch)
        # We log generic batch metrics here, individual winner metrics will be logged by Risk/Execution?
        # Or we log all candidates? Let's log count for now.
        latency = (time.time() - start_time) * 1000

        # We skip single-winner telemetry here because we don't pick one yet.
        # But we can log that we finished.

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


# --- GLOBAL INSTANCE FOR PERSISTENCE ---
# We must instantiate the agent ONCE so that:
# 1. Physics Engine state (Kalman Filter) is preserved between ticks.
# 2. LSTM hidden states are preserved.
# 3. Memory Service connections remain stable.
_analyst_agent_instance = AnalystAgent()


def analyst_node(state: AgentState) -> AgentState:
    """
    LangGraph Node Wrapper (Synchronous).
    Uses the persistent global agent instance.
    """
    return asyncio.run(_analyst_agent_instance.analyze(state))
