import logging
import numpy as np
import time
from typing import Optional

from app.agent.state import AgentState, OrderSide, TradingStatus
from app.adapters.market import MarketAdapter
from app.adapters.llm import LLMAdapter
from app.adapters.sentiment import SentimentAdapter
from app.lib.kalman import KinematicKalmanFilter
from app.lib.memory import FractalMemory
from app.services.global_state import get_global_state_service, get_current_snapshot_id

logger = logging.getLogger(__name__)


class AnalystAgent:
    """
    The Analyst Node acts as the Quantitative Strategist.
    It implements the 'Sensor Fusion' pipeline:
    Data -> Fractal Differentiation -> Kalman Filter -> LLM Inference -> Signal.
    """

    def __init__(self):
        self.market = MarketAdapter()
        self.llm = LLMAdapter()
        self.sentiment = SentimentAdapter()
        self.kf = KinematicKalmanFilter()

    def analyze(self, state: AgentState) -> AgentState:
        symbol = state.get("symbol", "SPY")
        start_time = time.time()
        success = True
        error_msg = None

        try:
            # --- Step 1: Sensory (Data Collection) ---
            current_price = self.market.get_current_price(symbol)
            historic_returns = self.market.get_historic_returns(symbol)

            # CRITICAL: Update state immediately
            state["price"] = current_price
            state["historic_returns"] = historic_returns

            # Reconstruct raw price history from returns
            # We work backwards from current price
            prices = [current_price]
            for r in reversed(historic_returns):
                denom = 1.0 + r
                if denom == 0:
                    prices.append(prices[-1])
                else:
                    prev_price = prices[-1] / denom
                    prices.append(prev_price)

            # Chronological order: [Oldest ... Newest]
            prices_chronological = list(reversed(prices))

            # --- Step 2: Transmission (Fractional Memory) ---
            # Apply Fractional Differentiation to get a stationary series
            # that preserves trend memory.
            frac_series = FractalMemory.frac_diff(prices_chronological, d=0.4)

            # --- Step 3: Engine (Physics) ---
            # We run the Kalman Filter on the FRACTIONALLY DIFFERENTIATED series.
            # This allows us to estimate the velocity/acceleration of the "stationary trend".

            # Warm up with last 10 points (or available)
            warmup_window = (
                frac_series[-11:-1] if len(frac_series) > 10 else frac_series[:-1]
            )
            for val in warmup_window:
                self.kf.update(val)

            # Update with the latest point
            latest_frac_val = frac_series[-1]
            est = self.kf.update(latest_frac_val)

            velocity = est.velocity
            acceleration = est.acceleration

            # TRACK PHYSICS OUTPUT
            state["velocity"] = velocity
            state["acceleration"] = acceleration

            # Get Regime from state if exists, else "Unknown"
            regime = state.get("regime", "Unknown")

            # --- Step 4: Cognition ---
            context_str = (
                f"Symbol: {symbol} | "
                f"Price: {current_price} | "
                f"FracDiff Velocity: {velocity:.4f} | "
                f"FracDiff Accel: {acceleration:.4f} | "
                f"Regime: {regime}"
            )

            # TRACK LLM INVOCATION
            llm_start = time.time()
            signal_data = self.llm.get_trade_signal(context_str)
            llm_latency = (time.time() - llm_start) * 1000

            # Save Gemma2 metrics
            state_service = get_global_state_service()
            snapshot_id = get_current_snapshot_id()
            if state_service and snapshot_id:
                state_service.save_model_metrics(
                    snapshot_id=snapshot_id,
                    model_name="gemma2_9b",
                    latency_ms=llm_latency,
                    thought_process=signal_data.get("raw_response"),
                    prediction={
                        "signal": signal_data.get("signal_side"),
                        "confidence": signal_data.get("signal_confidence"),
                    },
                    tokens_in=signal_data.get("tokens_input"),
                    tokens_out=signal_data.get("tokens_output"),
                    confidence=signal_data.get("signal_confidence"),
                )

            # TRACK SENTIMENT (Optional - can be used for additional context)
            sentiment_result = self.sentiment.analyze(context_str)
            if state_service and snapshot_id:
                state_service.save_model_metrics(
                    snapshot_id=snapshot_id,
                    model_name="finbert",
                    latency_ms=sentiment_result.get("latency_ms", 0),
                    prediction={
                        "label": sentiment_result.get("label"),
                        "score": sentiment_result.get("score"),
                    },
                    confidence=sentiment_result.get("score"),
                )

            # --- Step 5: Output (Decision Mapping) ---
            raw_signal = signal_data.get("signal_side", "FLAT").upper()
            confidence = float(signal_data.get("signal_confidence", 0.0))
            reasoning = signal_data.get("reasoning", "No reasoning provided.")

            signal_side = OrderSide.FLAT.value
            if raw_signal == "BUY":
                signal_side = OrderSide.BUY.value
            elif raw_signal == "SELL":
                signal_side = OrderSide.SELL.value

            state["signal_side"] = signal_side
            state["signal_confidence"] = confidence
            state["reasoning"] = reasoning

            # Logging
            log_msg = (
                f"ANALYST: 🧠 Signal {signal_side} | "
                f"Conf {confidence:.2f} | "
                f"FV {velocity:.4f} | "
                f"FA {acceleration:.4f} | "
                f"{reasoning}"
            )
            print(log_msg)
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(log_msg)

        except Exception as e:
            success = False
            error_msg = f"ANALYST: 💥 CRASH: {e}"
            print(error_msg)
            logger.exception(error_msg)

            # Fail safe
            state["signal_side"] = OrderSide.FLAT.value
            state["signal_confidence"] = 0.0
            state["reasoning"] = f"Error: {e}"
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(error_msg)

        finally:
            # TRACK AGENT PERFORMANCE
            latency = (time.time() - start_time) * 1000
            state_service = get_global_state_service()
            snapshot_id = get_current_snapshot_id()
            if state_service and snapshot_id:
                state_service.save_agent_metrics(
                    snapshot_id=snapshot_id,
                    agent_name="analyst",
                    latency_ms=latency,
                    success=success,
                    output_data={
                        "signal_side": state.get("signal_side"),
                        "confidence": state.get("signal_confidence"),
                        "velocity": state.get("velocity"),
                        "acceleration": state.get("acceleration"),
                    },
                    error=error_msg,
                )

        return state


def analyst_node(state: AgentState) -> AgentState:
    agent = AnalystAgent()
    return agent.analyze(state)
