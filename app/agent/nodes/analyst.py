import logging
import numpy as np

from app.agent.state import AgentState, OrderSide, TradingStatus
from app.adapters.market import MarketAdapter
from app.adapters.llm import LLMAdapter
from app.lib.kalman import KinematicKalmanFilter
from app.lib.memory import FractalMemory

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
        self.kf = KinematicKalmanFilter()

    def analyze(self, state: AgentState) -> AgentState:
        symbol = state.get("symbol", "SPY")

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

            signal_data = self.llm.get_trade_signal(context_str)

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

        return state


def analyst_node(state: AgentState) -> AgentState:
    agent = AnalystAgent()
    return agent.analyze(state)
