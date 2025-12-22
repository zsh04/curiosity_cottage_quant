import logging
import asyncio
import time

from typing import Dict, Any
from opentelemetry import trace

from app.agent.state import AgentState
from app.services.market import MarketService
from app.services.feynman_bridge import FeynmanBridge
from app.services.forecast import TimeSeriesForecaster

# from app.services.forecasting import ForecastingService # Deprecated
from app.services.reasoning import ReasoningService
from app.services.memory import MemoryService
from app.core import metrics as business_metrics
from app.strategies.lstm import LSTMPredictionStrategy
from app.strategies import ENABLED_STRATEGIES
from app.services.global_state import (
    get_global_state_service,
    get_current_snapshot_id,
    save_model_checkpoint,
    load_latest_checkpoint,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class BoydAgent:
    """
    The Council of Giants: 'Boyd' (The Strategist).
    Uses 'Feynman' (Physics) for OODA Loop Orientation.
    Implements the core Analyst/Strategist logic.
    """

    def __init__(self):
        # Instantiate Services
        self.market = MarketService()
        self.feynman_map: Dict[str, FeynmanBridge] = {}  # Per-symbol Physics Bridge
        self.oracle = TimeSeriesForecaster()
        self.reasoning = ReasoningService()
        self.memory = MemoryService()  # Quantum Memory

        # Strategy & Persistence
        self.lstm_model = LSTMPredictionStrategy()

        # Initialize The Council
        self.strategies = [Cls() for Cls in ENABLED_STRATEGIES]
        logger.info(f"BOYD: Initialized Council with {len(self.strategies)} experts.")
        try:
            # TRY DB LOAD
            blob = load_latest_checkpoint("boyd_bi_lstm")
            if blob:
                self.lstm_model.load_state_bytes(blob)
                logger.info("BOYD: Loaded LSTM state from Database.")
            else:
                # FALLBACK TO FILE (Migration support)
                logger.info("BOYD: No DB checkpoint found. Trying file...")
                self.lstm_model.load_state("data/models/lstm_analyst.pkl")

        except Exception as e:
            logger.warning(f"Failed to load LSTM state: {e}")

        self.cycle_count = 0

    def _get_feynman_bridge(self, symbol: str) -> FeynmanBridge:
        """
        Factory method to get or create a unique FeynmanBridge for a symbol.
        Ensures strict state isolation.
        """
        if symbol not in self.feynman_map:
            logger.info(f"BOYD: ⚛️ Spawning new Feynman Bridge for {symbol}")
            self.feynman_map[symbol] = FeynmanBridge()
        return self.feynman_map[symbol]

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
            # Get Isolated Physics Engine (Feynman)
            feynman = self._get_feynman_bridge(symbol)

            # --- PHASE 0: WARM-UP (If needed) ---
            if not feynman.is_initialized:
                startup_bars = await asyncio.to_thread(
                    self.market.get_startup_bars, symbol, limit=100
                )
                # Warmup Physics
                await asyncio.to_thread(feynman.calculate_kinematics, startup_bars)

                # Warmup/Init LSTM (feed returns)
                import pandas as pd

                if startup_bars:
                    df_warmup = pd.DataFrame({"close": startup_bars})
                    self.lstm_model.calculate_signal(df_warmup)
                    logger.info(f"🔥 BOYD: Warm-up complete for {symbol}")

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
            physics_history = history.copy()
            if current_price > 0:
                physics_history.append(current_price)

            # --- Step 2: PHYSICS (Kinematics & Regime) ---
            if feynman.is_initialized and current_price > 0:
                kinematics = await asyncio.to_thread(
                    feynman.calculate_kinematics, new_price=current_price
                )
            else:
                kinematics = await asyncio.to_thread(
                    feynman.calculate_kinematics, prices=physics_history
                )

            logger.info(f"DEBUG: {symbol} Raw Velocity: {kinematics.get('velocity')}")

            # Regime Analysis
            internal_buffer = feynman.price_history_buffer

            regime_analysis = await asyncio.to_thread(
                feynman.analyze_regime, internal_buffer
            )
            hurst_analysis = await asyncio.to_thread(
                feynman.calculate_hurst_and_mode, physics_history
            )
            qho_analysis = await asyncio.to_thread(
                feynman.calculate_qho_levels, physics_history
            )

            physics_context = {
                **kinematics,
                **regime_analysis,
                **hurst_analysis,
                **qho_analysis,
            }

            # --- Step 2.1: THE COUNCIL (Algorithmic Signals) ---
            strat_signals = {}
            if history:
                try:
                    import pandas as pd

                    dates = market_snapshot.get("dates", [])
                    if len(dates) == len(history):
                        df = pd.DataFrame(
                            {"close": history}, index=pd.to_datetime(dates)
                        )
                    else:
                        df = pd.DataFrame({"close": history})

                    for strat in self.strategies:
                        try:
                            # Most strategies expect a DF
                            sig = strat.calculate_signal(df)
                            strat_signals[strat.name] = sig  # -1.0 to 1.0
                        except Exception as e:
                            logger.warning(f"Strategy {strat.name} failed: {e}")
                except Exception as e:
                    logger.error(f"Council Session Failed: {e}")

            # --- Step 2.5: STRATEGY (LSTM Model) ---
            lstm_signal = 0.0
            if history:
                import pandas as pd

                df_latest = pd.DataFrame({"close": history})
                lstm_signal = self.lstm_model.calculate_signal(df_latest)

            # Persistence Check
            self.cycle_count += 1
            if self.cycle_count % 100 == 0:
                blob = self.lstm_model.get_state_bytes()
                if blob:
                    await asyncio.to_thread(save_model_checkpoint, "boyd_bi_lstm", blob)
                    logger.info("💾 BOYD: Saved LSTM checkpoint to Database.")

            # --- Step 3: THE UNIFIED ORACLE (Forecast + Memory) ---
            sentiment_snapshot = market_snapshot.get("sentiment", {})

            # Get Context Tensor (Last 64 bars)
            oracle_context_list = history[-64:] if history else []
            import torch

            context_tensor = torch.tensor(oracle_context_list, dtype=torch.float32)

            oracle_result = await self.oracle.predict_ensemble(
                context_tensor=context_tensor,
                current_prices=history,  # For RAG normalization
            )

            # Extract Components
            forecast = oracle_result.get("components", {}).get("chronos", {})
            historical_regimes = oracle_result.get("components", {}).get("raf", {})
            oracle_signal_side = oracle_result.get("signal", "NEUTRAL")
            oracle_confidence = oracle_result.get("confidence", 0.0)

            # --- Step 4: COGNITION (Reasoning / Signal) ---
            if not skip_llm:
                reasoning_context = {
                    "market": market_snapshot,
                    "physics": physics_context,
                    "forecast": forecast,
                    "regime_memory": historical_regimes,
                    "oracle_signal": {
                        "side": oracle_signal_side,
                        "confidence": oracle_confidence,
                        "reasoning": oracle_result.get("reasoning", ""),
                    },
                    "sentiment": sentiment_snapshot,
                    "strategies": {
                        "lstm_signal": lstm_signal,
                        **strat_signals,
                    },  # Inject Council & LSTM
                }
                signal_result = await self.reasoning.generate_signal(reasoning_context)
            else:
                # OPTIMIZATION: Skip LLM for non-primary candidates
                signal_result = {
                    "signal_side": oracle_signal_side
                    if oracle_signal_side != "NEUTRAL"
                    else "FLAT",
                    "signal_confidence": oracle_confidence,
                    "reasoning": f"Oracle Optimization: {oracle_result.get('reasoning', 'Skipped LLM')}",
                }

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
                    "chronos_forecast": forecast,  # Propagate real forecast
                    "success": True,
                }
            )

            return result_packet

        except Exception as e:
            logger.error(f"BOYD: Single Analysis Failed for {symbol}: {e}")
            result_packet["reasoning"] = f"CRASH: {e}"
            return result_packet

    async def analyze(self, state: AgentState) -> AgentState:
        """
        Quantum Batch Analysis (OODA Loop).
        """
        analysis_start_time = time.time()
        candidates = state.get("watchlist", [])

        target_symbol = state.get("symbol", "SPY")
        primary_in_batch = any(c.get("symbol") == target_symbol for c in candidates)

        if not primary_in_batch:
            candidates.insert(0, {"symbol": target_symbol})

        if not candidates:
            # Fallback
            logger.warning(
                f"BOYD: No candidates found. Fallback to single symbol: {target_symbol}"
            )
            candidates = [{"symbol": target_symbol}]

        primary_symbol = state.get("symbol", "SPY")
        tasks = []

        # --- PARALLEL EXECUTION (Conditional LLM) ---
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
            candidate = candidates[i].copy()

            if isinstance(res, dict):
                candidate.update(res)
                if candidate.get("symbol") == primary_symbol:
                    primary_data = candidate
            elif isinstance(res, Exception):
                logger.error(f"BOYD: Error analyzing {candidate.get('symbol')}: {res}")
                candidate["error"] = str(res)
                candidate["success"] = False

            enriched_candidates.append(candidate)

        state["analysis_reports"] = enriched_candidates
        state["candidates"] = enriched_candidates

        if primary_data and primary_data.get("success"):
            # Check for Physics Veto (CRITICAL Regime)
            if primary_data.get("regime") == "Critical":
                logger.warning(
                    f"BOYD: Primary {primary_symbol} is in CRITICAL regime. Initiating searching for alternative..."
                )
                primary_data = None  # Discard

        if not primary_data:
            # Fallback / Auto-Selection: Pick highest confidence success
            valid_candidates = [
                c
                for c in enriched_candidates
                if c.get("success") and c.get("regime") != "Critical"
            ]
            if valid_candidates:
                # Sort by confidence desc
                valid_candidates.sort(
                    key=lambda x: x.get("signal_confidence", 0.0), reverse=True
                )
                primary_data = valid_candidates[0]
                primary_symbol = primary_data.get("symbol")
                state["symbol"] = primary_symbol  # Update State
                logger.info(
                    f"BOYD: 🔄 Switched Primary to {primary_symbol} (Conf: {primary_data.get('signal_confidence'):.2f})"
                )
            else:
                logger.warning("BOYD: No valid alternative candidates found.")

        # HOIST PRIMARY SIGNAL
        if primary_data and primary_data.get("success"):
            logger.info(f"BOYD: 🚀 Hoisting signal for {primary_symbol}")
            state["signal_side"] = primary_data.get("signal_side", "FLAT")
            state["signal_confidence"] = primary_data.get("signal_confidence", 0.0)
            state["regime"] = primary_data.get("regime", "Gaussian")
            state["reasoning"] = primary_data.get("reasoning", "")

            state["current_alpha"] = primary_data.get("current_alpha", 2.0)
            state["velocity"] = primary_data.get("velocity", 0.0)
            state["acceleration"] = primary_data.get("acceleration", 0.0)
            state["price"] = primary_data.get("price", 0.0)
            state["chronos_forecast"] = primary_data.get(
                "chronos_forecast", {"trend": "Neutral", "confidence": 0.0}
            )
        else:
            logger.warning(
                "BOYD: Primary symbol analysis failed or missing. State not updated."
            )

        successful = [c for c in enriched_candidates if c.get("success")]
        logger.info(
            f"BOYD: Batch Analysis Complete. {len(successful)}/{len(enriched_candidates)} successful."
        )

        # Telemetry
        latency = (time.time() - analysis_start_time) * 1000
        business_metrics.analyst_latency.record(latency)
        business_metrics.candidate_count.record(len(candidates))
        business_metrics.signals_total.add(len(successful))

        logger.info(f"⏱️ Boyd Latency: {latency:.2f}ms")

        return state


# --- GLOBAL INSTANCE ---
_boyd_agent_instance = BoydAgent()


async def boyd_node(state: AgentState) -> AgentState:
    """
    LangGraph/Pipeline Node Wrapper (Async) for Boyd (The Strategist).
    """
    return await _boyd_agent_instance.analyze(state)
