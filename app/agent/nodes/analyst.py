import logging
import numpy as np

from app.agent.state import AgentState, OrderSide, TradingStatus
from app.adapters.market import MarketAdapter
from app.adapters.llm import LLMAdapter
from app.lib.kalman import KinematicKalmanFilter

logger = logging.getLogger(__name__)


def analyst_node(state: AgentState) -> AgentState:
    """
    The Analyst Node acts as the Quantitative Strategist.
    It processes market data, applies kinematic physics, and uses an LLM
    to generate trading signals.
    """
    # --- Input ---
    symbol = state.get("symbol", "SPY")

    # --- Initialization ---
    market = MarketAdapter()
    llm = LLMAdapter()
    kf = KinematicKalmanFilter()

    try:
        # --- Step 1: Sensory (Data Collection) ---
        current_price = market.get_current_price(symbol)
        historic_returns = market.get_historic_returns(symbol)

        # CRITICAL: Update state immediately
        state["price"] = current_price
        state["historic_returns"] = historic_returns

        # --- Step 2: Math - Kinematics ---
        # We reconstruct the price path from returns to "warm up" the Kalman Filter
        # and get a meaningful velocity estimate.

        # 1. Reconstruct prices backwards
        prices = [current_price]
        for r in reversed(historic_returns):
            denom = 1.0 + r
            if denom == 0:
                prices.append(prices[-1])
            else:
                prev_price = prices[-1] / denom
                prices.append(prev_price)

        # 2. Sequential Update (Oldest -> Newest)
        prices_chronological = list(reversed(prices))

        velocity = 0.0

        # Run KF on history
        for p in prices_chronological:
            est = kf.update(p)
            velocity = est.velocity

        # One final update on current price (already in list, but ensures fresh state)
        # Note: prices_chronological includes current_price as the last element,
        # so the loop above already leaves KF in the state of current_price.

        # --- Step 3: Cognition ---
        # Calculate Volatility (100-Day Std Dev)
        if historic_returns:
            recent_returns = historic_returns[-100:]
            std_dev = float(np.std(recent_returns))
        else:
            std_dev = 0.0

        context_str = (
            f"Asset: {symbol} | "
            f"Price: {current_price} | "
            f"Velocity: {velocity:.4f} | "
            f"100-Day Vol: {std_dev:.2%}"
        )

        signal_data = llm.get_trade_signal(context_str)

        # --- Step 4: Decision Mapping ---
        raw_signal = signal_data.get("signal_side", "FLAT").upper()
        confidence = float(signal_data.get("signal_confidence", 0.0))
        reasoning = signal_data.get("reasoning", "No reasoning provided.")

        if raw_signal == "BUY":
            signal_side = (
                OrderSide.BUY.value
            )  # Store as string for JSON serialization friendliness/TypedDict
        elif raw_signal == "SELL":
            signal_side = OrderSide.SELL.value
        else:
            signal_side = OrderSide.FLAT.value

        state["signal_side"] = signal_side
        state["signal_confidence"] = confidence
        state["reasoning"] = reasoning

        # --- Step 5: Logging ---
        log_msg = (
            f"ANALYST: 🧠 Signal {signal_side} | "
            f"Conf {confidence:.2f} | "
            f"Vel {velocity:.4f} | "
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
