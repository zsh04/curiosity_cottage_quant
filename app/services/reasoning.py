from app.adapters.llm import LLMAdapter
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ReasoningService:
    """
    Reasoning Service: The 'Prefrontal Cortex' of the system.
    Synthesizes multi-modal data (Market, Physics, Forecast, Sentiment)
    to generate a final high-level trading decision via LLM.
    """

    def __init__(self):
        self.llm = LLMAdapter()

    def generate_signal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        The "God Prompt" Execution.

        Args:
            context: A dictionary containing:
                - market: {symbol, price, news_context}
                - physics: {velocity, acceleration, regime}
                - forecast: {trend, expected_price}
                - sentiment: {score, label}

        Returns:
            {
                "signal_side": "BUY" | "SELL" | "FLAT",
                "signal_confidence": float,
                "reasoning": str
            }
        """
        # Unpack Context for Prompt Construction
        market = context.get("market", {})
        physics = context.get("physics", {})
        forecast = context.get("forecast", {})
        sentiment = context.get("sentiment", {})

        # Construct the God Prompt
        prompt_text = f"""
You are the Chief Investment Officer of a quantitative hedge fund. 
Your goal is to maximize alpha while strictly managing risk.
Analyze the following multi-modal sensor data for {market.get("symbol", "ASSET")} and make a trading decision.

--- SENSOR DATA ---

1. MARKET DATA
   - Price: ${market.get("price", 0.0):.2f}
   - News Context: {market.get("news_context", "No news.")}

2. PHYSICS ENGINE (Kinematics & Thermodynamics)
   - Velocity (Trend): {physics.get("velocity", 0.0):.4f}
   - Acceleration (Momentum): {physics.get("acceleration", 0.0):.4f}
   - Market Regime: {physics.get("regime", "Unknown")} (Alpha: {physics.get("alpha", 0.0):.2f})

3. FORECAST EXTENSION (Chronos AI)
   - Predicted Trend: {forecast.get("trend", "NEUTRAL")}
   - Expected Price (10m): ${forecast.get("expected_price", 0.0):.2f}
   - Confidence: {forecast.get("confidence", 0.0):.2f}

4. SENTIMENT ANALYSIS (FinBERT)
   - Label: {sentiment.get("label", "neutral")}
   - Score: {sentiment.get("score", 0.0):.2f}

--- MISSION ---
Synthesize these signals. Look for confluence.
- If Physics shows positive velocity AND Forecast is Bullish -> STRONG BUY.
- If Physics shows negative acceleration AND Sentiment is Negative -> SELL.
- If Regime is 'Critical' or 'Levy Stable', be extremely cautious (FLAT/REDUCE).

--- OUTPUT FORMAT ---
Respond ONLY with this JSON structure:
{{
  "signal_side": "BUY" or "SELL" or "FLAT",
  "signal_confidence": 0.0 to 1.0,
  "reasoning": "A concise 1-sentence explanation of your decision citing specific metrics."
}}
"""
        logger.info("🧠 ReasoningService: Invoking LLM for logic synthesis...")

        # Call LLM Logic
        # We rely on the adapter's built-in JSON parsing and fallback
        # But allow passing the constructed prompt directly if needed,
        # Here we pass the prompt as the 'context' argument to get_trade_signal which usually expects context strings,
        # but looking at LLMAdapter.get_trade_signal, it wraps the input in another prompt.
        # To avoid double prompting, we might need to adjust or just pass the data summary.
        # Start simple: Pass the formatted data block.

        # Refined call:
        # LLMAdapter.get_trade_signal wraps input in "Based on... context...".
        # So we should pass just the data block, not the full prompt with instructions,
        # OR we use `llm.infer` directly if we want full control.
        # The Architect instruction said "Call get_trade_signal".
        # Let's pass the rich data block as the context.

        data_block = f"""
Price: ${market.get("price", 0.0)}
News: {market.get("news_context", "None")}
Physics: Velocity={physics.get("velocity", 0.0):.4f}, Accel={physics.get("acceleration", 0.0):.4f}, Regime={physics.get("regime", "Unknown")}
Forecast: {forecast.get("trend", "Neutral")} (Conf: {forecast.get("confidence", 0.0)})
Sentiment: {sentiment.get("label", "Neutral")} (Score: {sentiment.get("score", 0.0)})
"""
        result = self.llm.get_trade_signal(data_block)

        return {
            "signal_side": result.get("signal_side", "FLAT"),
            "signal_confidence": result.get("signal_confidence", 0.0),
            "reasoning": result.get("reasoning", "Analysis failed."),
        }
