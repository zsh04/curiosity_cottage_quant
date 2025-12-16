import logging
import numpy as np
import time
from typing import Optional

from app.agent.state import AgentState, OrderSide, TradingStatus
from app.adapters.market import MarketAdapter
from app.adapters.llm import LLMAdapter
from app.adapters.sentiment import SentimentAdapter
from app.adapters.chronos import ChronosAdapter
from app.lib.kalman import KinematicKalmanFilter
from app.lib.memory import FractalMemory
from app.lib.physics.heavy_tail import HeavyTailEstimator
from app.services.global_state import get_global_state_service, get_current_snapshot_id

logger = logging.getLogger(__name__)


class AnalystAgent:
    """
    The Analyst Node acts as the Quantitative Strategist.
    It implements the 'Sensor Fusion' pipeline:
    Data -> Fractal Differentiation -> Kalman Filter -> Chronos Forecast -> LLM Inference -> Signal.
    """

    def __init__(self):
        self.market = MarketAdapter()
        self.llm = LLMAdapter()
        self.sentiment = SentimentAdapter()
        self.chronos = ChronosAdapter()
        self.kf = KinematicKalmanFilter()
        self.physics = HeavyTailEstimator(window_size=100)  # Window for Hill Estimator

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

            # TRACK PHYSICS OUTPUT (Kalman)
            state["velocity"] = velocity
            state["acceleration"] = acceleration

            # --- Step 3.1: Heavy Tail Physics (Alpha & Regime) ---
            # Update HeavyTailEstimator with new returns
            # We need simple returns or log returns? HeavyTail usually uses Absolute Returns for Tail Index.
            # Passing relevant data. Check signatures.
            # Assuming update(price) or update(returns)?
            # Standard implementation usually takes returns.
            # Let's assume input raw prices and it calculates, OR we pass returns.
            # Looking at imports, it's custom lib.
            # Best guess: update(price) or update_returns(ret).
            # I'll rely on it keeping internal buffer if I pass value, OR I compute on history.

            # Since I don't see the file, I'll pass the whole history to `compute_alpha` if it supports it,
            # Or assume incremental `update`.
            # Use historic_returns from state to calculate Alpha statelessly
            # historic_returns are [t-1, t-2, ...]? OR chronological?
            # In analyze(), historic_returns comes from market.get_historic_returns.
            # Usually [oldest ... newest].
            # Hill estimator sorts them anyway.

            raw_returns = state.get("historic_returns", [])
            current_alpha = 3.0  # Default
            regime = "Gaussian"

            if raw_returns:
                current_alpha = HeavyTailEstimator.hill_estimator(np.array(raw_returns))
                regime = HeavyTailEstimator.detect_regime(current_alpha)

            state["current_alpha"] = current_alpha
            state["regime"] = regime

            # --- Step 3.5: Chronos Forecast (Probabilistic Future) ---
            forecast_context = ""
            chronos_start = time.time()

            # Use last 30 prices for forecast context (or available)
            recent_prices = (
                prices_chronological[-30:]
                if len(prices_chronological) >= 30
                else prices_chronological
            )
            forecast = self.chronos.predict(recent_prices, horizon=10)
            state["chronos_forecast"] = forecast or {}

            chronos_latency = (time.time() - chronos_start) * 1000

            if forecast:
                # Extract metrics
                median_forecast = forecast.get("median", [])
                low_forecast = forecast.get("low", [])
                high_forecast = forecast.get("high", [])

                if median_forecast:
                    # Trend: Is median forecast > current price?
                    forecast_median_value = median_forecast[-1]  # Last forecasted point
                    trend = (
                        "Bullish"
                        if forecast_median_value > current_price
                        else "Bearish"
                    )

                    # Uncertainty: Spread between high/low quantiles
                    if low_forecast and high_forecast:
                        uncertainty_spread = abs(high_forecast[-1] - low_forecast[-1])
                        uncertainty_pct = (uncertainty_spread / current_price) * 100
                        confidence_level = "Low" if uncertainty_pct > 2.0 else "High"
                    else:
                        confidence_level = "Medium"

                    forecast_context = (
                        f"QUANTITATIVE FORECAST: Chronos predicts a {trend} trend "
                        f"over the next 10 ticks with {confidence_level} confidence."
                    )

                    logger.info(
                        f"🔮 Chronos: {trend} trend, {confidence_level} confidence"
                    )

                    # Track Chronos performance
                    state_service = get_global_state_service()
                    snapshot_id = get_current_snapshot_id()
                    if state_service and snapshot_id:
                        state_service.save_model_metrics(
                            snapshot_id=snapshot_id,
                            model_name="chronos_t5_small",
                            latency_ms=chronos_latency,
                            prediction={
                                "trend": trend,
                                "median_forecast": median_forecast[-1],
                                "confidence_level": confidence_level,
                            },
                            confidence=1.0 if confidence_level == "High" else 0.5,
                        )
            else:
                forecast_context = "FORECAST: Unavailable (System Offline)."
                trend = "Unknown"
                confidence_level = "Unknown"
                logger.warning("⚠️  Chronos forecast unavailable")

            # --- Step 3.6: News Fetching & Sentiment Analysis (FinBERT) ---
            sentiment_context = ""
            sentiment_label = "neutral"
            sentiment_score = 0.0
            top_headlines_str = ""

            # Fetch live news headlines
            logger.info(f"📰 Fetching news for {symbol}...")
            news_headlines = self.market.get_news(symbol, limit=5)

            if news_headlines:
                # Handle list of dicts (from API/Mock) or list of strings
                processed_headlines = []
                for item in news_headlines:
                    if isinstance(item, dict):
                        processed_headlines.append(item.get("title", ""))
                    elif isinstance(item, str):
                        processed_headlines.append(item)

                # Filter empty strings
                processed_headlines = [h for h in processed_headlines if h]

                # Analyze sentiment on combined headlines
                combined_headlines = " | ".join(processed_headlines)
                top_headlines_str = " | ".join(
                    processed_headlines[:3]
                )  # Top 3 for context

                sentiment_result = self.sentiment.analyze(combined_headlines)

                if sentiment_result and not sentiment_result.get("error"):
                    sentiment_label = sentiment_result.get("sentiment", "neutral")
                    sentiment_score = sentiment_result.get("score", 0.0)

                    logger.info(
                        f"📊 FinBERT: {sentiment_label} ({sentiment_score:.2f}) "
                        f"from {len(news_headlines)} headlines"
                    )

                    # Track FinBERT metrics
                    state_service = get_global_state_service()
                    snapshot_id = get_current_snapshot_id()
                    if state_service and snapshot_id:
                        state_service.save_model_metrics(
                            snapshot_id=snapshot_id,
                            model_name="finbert",
                            latency_ms=sentiment_result.get("latency_ms", 0),
                            prediction={
                                "label": sentiment_label,
                                "score": sentiment_score,
                                "headlines_count": len(news_headlines),
                            },
                            confidence=sentiment_score,
                        )
                else:
                    logger.warning("⚠️  FinBERT sentiment analysis failed")
            else:
                # No news available - use neutral sentiment
                logger.warning(
                    f"⚠️  No news available for {symbol}, defaulting to neutral sentiment"
                )
                sentiment_label = "neutral"
                sentiment_score = 0.0
                top_headlines_str = "No recent news available"

            # --- Step 4: Cognition (God Prompt for LLM) ---
            # Construct comprehensive context integrating ALL signals
            god_prompt = f"""MARKET INTELLIGENCE REPORT FOR {symbol}

CURRENT STATE:
- Price: ${current_price:.2f}
- Regime: {regime}

PHYSICS ENGINE:
- Kinematic Velocity: {velocity:.4f}
- Kinematic Acceleration: {acceleration:.4f}

PROBABILISTIC FORECAST (Chronos-2):
- Trend Direction: {trend}
- Forecast Confidence: {confidence_level}

NEWS SENTIMENT (FinBERT):
- Sentiment: {sentiment_label.upper()}
- Confidence Score: {sentiment_score:.2f}
- Recent Headlines: {top_headlines_str}

Based on these multi-modal signals (Physics, Forecast, News Sentiment), provide a trading recommendation.
Respond in JSON format:
{{
  "signal_side": "BUY|SELL|FLAT",
  "signal_confidence": 0.0-1.0,
  "reasoning": "Concise explanation integrating all signals"
}}
"""

            # TRACK LLM INVOCATION
            llm_start = time.time()
            signal_data = self.llm.get_trade_signal(god_prompt)
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
