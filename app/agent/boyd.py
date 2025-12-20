import logging
import asyncio
import time

from typing import Dict, Any
from opentelemetry import trace

from app.agent.state import AgentState
from app.services.market import MarketService
from app.services.feynman import FeynmanEngine
from app.services.forecasting import ForecastingService
from app.services.reasoning import ReasoningService
from app.services.memory import MemoryService
from app.core import metrics as business_metrics
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
    The Council of Giants: 'Boyd' (The Strategist).
    Uses 'Feynman' (Physics) for OODA Loop Orientation.
    """

    def __init__(self):
        # Instantiate Services
        self.market = MarketService()
        self.physics_map: Dict[str, FeynmanEngine] = {}  # NEW: Per-symbol factory
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
                logger.info("BOYD: Loaded LSTM state from Database.")
            else:
                # FALLBACK TO FILE (Migration support)
                logger.info("BOYD: No DB checkpoint found. Trying file...")
                self.lstm_model.load_state("data/models/lstm_analyst.pkl")

        except Exception as e:
            logger.warning(f"Failed to load LSTM state: {e}")

        self.cycle_count = 0

    def _get_feynman_engine(self, symbol: str) -> FeynmanEngine:
        """
        Factory method to get or create a unique FeynmanEngine for a symbol.
        """
        if symbol not in self.physics_map:
            logger.info(f"BOYD: ⚛️ Spawning new Feynman Engine for {symbol}")
            self.physics_map[symbol] = FeynmanEngine()
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
            feynman = self._get_feynman_engine(symbol)

            # --- Step 1: SENSES (Market Data) ---
            market_snapshot = await asyncio.to_thread(
                self.market.get_market_snapshot, symbol
            )

            # Extract basics
            history = market_snapshot.get("history", [])
            current_price = market_snapshot.get("price", 0.0)

            # Infer High/Low/Volume if not in snapshot (often snapshot has full bar data)
            # Assuming market_snapshot has 'quote' or 'bar'
            # If simplistic, we use current_price for all
            high = market_snapshot.get("high", current_price)
            low = market_snapshot.get("low", current_price)
            volume = market_snapshot.get("volume", 1000.0)  # Default volume if missing
            trade_count = market_snapshot.get("trade_count", 100)  # Default

            # --- Step 2: FEYNMAN PHYSICS (Forces) ---
            # Update Feynman Engine
            forces = await asyncio.to_thread(
                feynman.calculate_forces,
                price=current_price,
                volume=volume,
                trade_count=trade_count,
                high=high,
                low=low,
            )

            logger.info(f"DEBUG: {symbol} Momentum: {forces.get('momentum')}")

            physics_context = forces

            # --- Step 2.5: STRATEGY (LSTM Model) ---
            # Update/Predict with latest data
            lstm_signal = 0.0
            if history:
                import pandas as pd  # Import locally to avoid top-level cost if rare

                df_latest = pd.DataFrame({"close": history})
                lstm_signal = self.lstm_model.calculate_signal(df_latest)

            # Persistence Check
            self.cycle_count += 1
            if self.cycle_count % 100 == 0:
                # Save to DB
                blob = self.lstm_model.get_state_bytes()
                if blob:
                    await asyncio.to_thread(save_model_checkpoint, "analyst_lstm", blob)
                    logger.info("💾 BOYD: Saved LSTM checkpoint to Database.")

            # --- Step 3: FUTURE (Forecasting) ---
            forecast = await asyncio.to_thread(
                self.forecasting.predict_trend, history, 10
            )

            # --- Step 3.5: MEMORY (Quantum Recall) ---
            sentiment_snapshot = market_snapshot.get("sentiment", {})

            # Mapping for Memory (Adapter)
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
                    "strategies": {"lstm_signal": lstm_signal},
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
                    "velocity": forces["velocity"],
                    "acceleration": 0.0,  # Not calculated in Feynman yet
                    "regime": forces["regime"],
                    "current_alpha": forces["current_alpha"],
                    "hurst": 0.5,  # Feynman maps this to Entropy/Nash
                    "strategy_mode": "AMBUSH"
                    if forces["regime"] == "AMBUSH"
                    else "SNIPER",
                    "price": market_snapshot.get("price", 0.0),
                    "history": history,
                    "chronos_forecast": forecast,
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
        Quantum Batch Analysis.
        """
        analysis_start_time = time.time()
        candidates = state.get("watchlist", [])

        target_symbol = state.get("symbol", "SPY")
        primary_in_batch = any(c.get("symbol") == target_symbol for c in candidates)

        if not primary_in_batch:
            candidates.insert(0, {"symbol": target_symbol})

        if not candidates:
            # Fallback
            candidates = [{"symbol": target_symbol}]

        primary_symbol = state.get("symbol", "SPY")
        tasks = []

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

        # Telemetry
        latency = (time.time() - analysis_start_time) * 1000
        business_metrics.analyst_latency.record(latency)
        business_metrics.candidate_count.record(len(candidates))
        business_metrics.signals_total.add(len(successful))

        return state


_analyst_agent_instance = AnalystAgent()


def analyst_node(state: AgentState) -> AgentState:
    """
    LangGraph Node Wrapper (Synchronous).
    """
    return asyncio.run(_analyst_agent_instance.analyze(state))
