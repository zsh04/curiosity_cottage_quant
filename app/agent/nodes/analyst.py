import logging
import asyncio
import time

from app.agent.state import AgentState
from app.services.market import MarketService
from app.services.physics import PhysicsService
from app.services.forecasting import ForecastingService
from app.services.reasoning import ReasoningService
from app.services.global_state import get_global_state_service, get_current_snapshot_id

logger = logging.getLogger(__name__)


class AnalystAgent:
    """
    The Analyst Node (Refactored).
    Acts as the Orchestrator of specialized services.
    "The Conductor, not the Orchestra."
    """

    def __init__(self):
        # Instantiate Services
        self.market = MarketService()
        self.physics = PhysicsService()
        self.forecasting = ForecastingService()
        self.reasoning = ReasoningService()

    async def analyze(self, state: AgentState) -> AgentState:
        """
        Asynchronous Analysis Logic.
        All blocking operations (CPU-bound math, Network IO) are offloaded to threads.
        This prevents blocking the asyncio event loop.
        """
        symbol = state.get("symbol", "SPY")
        start_time = time.time()
        success = True
        error_msg = None

        # Initialize output_data for telemetry
        telemetry_data = {}

        try:
            logger.info(f"🧠 ANALYST: Starting analysis for {symbol}...")

            # --- Step 1: SENSES (Market Data) ---
            # MarketService calls HTTP APIs (IO-bound) - offload to thread
            market_snapshot = await asyncio.to_thread(
                self.market.get_market_snapshot, symbol
            )

            # Update State with raw senses
            state["price"] = market_snapshot["price"]
            state["historic_returns"] = []  # Legacy key, kept for compatibility

            # Extract history for subsequent processing
            history = market_snapshot.get("history", [])

            # --- Step 2: PHYSICS (Kinematics & Regime) ---
            # CPU-bound operations - must run in threads to avoid blocking
            kinematics = await asyncio.to_thread(
                self.physics.calculate_kinematics, history
            )
            regime_analysis = await asyncio.to_thread(
                self.physics.analyze_regime, history
            )

            # Fuse Physics Data
            physics_context = {**kinematics, **regime_analysis}

            # Update State w/ Physics
            state["velocity"] = kinematics["velocity"]
            state["acceleration"] = kinematics["acceleration"]
            state["regime"] = regime_analysis["regime"]
            state["current_alpha"] = regime_analysis["alpha"]

            # --- Step 3: FUTURE (Forecasting) ---
            # ChronosAdapter does HTTP + heavy inference - offload to thread
            forecast = await asyncio.to_thread(
                self.forecasting.predict_trend, history, 10
            )

            # --- Step 4: COGNITION (Reasoning / Signal) ---
            # Construct Context for the "God Prompt"
            reasoning_context = {
                "market": market_snapshot,
                "physics": physics_context,
                "forecast": forecast,
                "sentiment": market_snapshot.get("sentiment", {}),
            }

            # LLMAdapter does HTTP calls - offload to thread
            signal_result = await asyncio.to_thread(
                self.reasoning.generate_signal, reasoning_context
            )

            # --- Step 5: OUTPUT (State Update) ---
            signal_side = signal_result.get("signal_side", "FLAT")
            confidence = signal_result.get("signal_confidence", 0.0)
            reasoning_text = signal_result.get("reasoning", "")

            state["signal_side"] = signal_side
            state["signal_confidence"] = confidence
            state["reasoning"] = reasoning_text

            # Clear legacy keys
            state["active_strategy"] = "LLM_Reasoning"
            state["strategy_score"] = 0.0

            # Log Result
            logger.info(
                f"💡 ANALYST SIGNAL: {signal_side} ({confidence:.2f}) | {reasoning_text}"
            )

            telemetry_data = {
                "signal_side": signal_side,
                "confidence": confidence,
                "reasoning": reasoning_text,
                "velocity": kinematics["velocity"],
                "regime": regime_analysis["regime"],
            }

        except Exception as e:
            success = False
            error_msg = f"ANALYST CRASH: {e}"
            logger.exception(error_msg)
            state["signal_side"] = "FLAT"
            state["reasoning"] = error_msg
            telemetry_data = {"error": str(e)}

        finally:
            # Telemetry / Metrics
            latency = (time.time() - start_time) * 1000

            # Save metrics to DB if Global State is available
            state_service = get_global_state_service()
            snapshot_id = get_current_snapshot_id()

            if state_service and snapshot_id:
                try:
                    state_service.save_agent_metrics(
                        snapshot_id=snapshot_id,
                        agent_name="analyst",
                        latency_ms=latency,
                        success=success,
                        output_data=telemetry_data,
                        error=error_msg,
                    )
                except Exception as e:
                    logger.error(f"Failed to save metrics: {e}")

        return state


async def analyst_node(state: AgentState) -> AgentState:
    """
    Async Node Wrapper.
    Since analyze() is now async, we call it directly without additional threading.
    """
    agent = AnalystAgent()
    return await agent.analyze(state)
