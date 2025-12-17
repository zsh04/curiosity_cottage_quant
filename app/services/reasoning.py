from app.adapters.llm import LLMAdapter
import logging
from typing import Dict, Any
from opentelemetry import trace
from app.core import metrics as business_metrics
import time
import math

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class ReasoningService:
    """
    Reasoning Service: The 'Prefrontal Cortex' of the system.
    Synthesizes multi-modal data (Market, Physics, Forecast, Sentiment)
    to generate a final high-level trading decision via LLM.
    """

    def __init__(self):
        self.llm = LLMAdapter()

    def _format_history(self, history: list) -> str:
        """Helper to format historical memory for prompt."""
        if not history:
            return "   - No relevant memory found."

        lines = []
        for i, h in enumerate(history, 1):
            meta = h.get("metadata", {})
            phy = meta.get("physics", {})
            sent = meta.get("sentiment", {})
            lines.append(
                f"   {i}. Date: {h.get('timestamp')} | "
                f"Regime: {phy.get('regime')} | "
                f"Sentiment: {sent.get('label')}"
            )
        return "\n".join(lines)

    def calculate_interference(
        self, news_A: Dict[str, Any], news_B: Dict[str, Any]
    ) -> float:
        """
        Calculate Quantum Interference between two news signals.
        Interference = 2 * sqrt(P_A * P_B) * cos(Theta)
        """
        try:
            # Propensities (Sigmoid of score)
            # Assuming score is -1 to 1. Sigmoid maps to 0-1 probability.
            def sigmoid(x):
                return 1 / (1 + math.exp(-x))

            score_A = news_A.get("score", 0.0)
            score_B = news_B.get("score", 0.0)

            P_A = sigmoid(score_A)
            P_B = sigmoid(score_B)

            # Phase Theta: Divergence creates shift
            # Heuristic: Max divergence (2.0) = 2pi? User said "abs(diff) * pi".
            theta = abs(score_A - score_B) * math.pi

            # Interference Term
            # Constructive (>0): Signals reinforce
            # Destructive (<0): Signals cancell/confuse
            interference = 2 * math.sqrt(P_A * P_B) * math.cos(theta)

            return float(interference)
        except Exception as e:
            logger.error(f"Quantum Interference calc failed: {e}")
            return 0.0

    @tracer.start_as_current_span("reasoning_generate_signal")
    def generate_signal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        The "God Prompt" Execution.

        Args:
            context: A dictionary containing:
                - market: {symbol, price, news_context, recent_news}
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

        # --- QUANTUM SENTIMENT ANALYSIS ---
        # Extract recent news items (Requires MarketService to pass 'recent_news' list)
        recent_news = market.get("recent_news", [])
        if len(recent_news) >= 2:
            news_A = recent_news[0]
            news_B = recent_news[1]
            interference = self.calculate_interference(news_A, news_B)
        elif len(recent_news) == 1:
            # Interference with itself? Constructive.
            interference = self.calculate_interference(recent_news[0], recent_news[0])
        else:
            interference = 0.0

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

4. SENTIMENT ANALYSIS (FinBERT + Quantum)
   - Label: {sentiment.get("label", "neutral")}
   - Score: {sentiment.get("score", 0.0):.2f}
   - Quantum Interference: {interference:.4f} (Negative = Noise/Confusion, Positive = Resonance)

5. HISTORICAL PRECEDENTS (Memory Service: Top 3 Similar Regimes)
{self._format_history(market.get("historical_regimes", []))}

--- MISSION ---
Synthesize these signals. Look for confluence.
- If Physics shows positive velocity AND Forecast is Bullish -> STRONG BUY.
- If Physics shows negative acceleration AND Sentiment is Negative -> SELL.
- If Regime is 'Critical' or 'Levy Stable', be extremely cautious (FLAT/REDUCE).
- If Quantum Interference is NEGATIVE, sentiment is conflicted/noisy. Reduce confidence.
- If current state mirrors a historical CRASH, bias towards SELL/FLAT.

--- OUTPUT FORMAT ---
Respond ONLY with this JSON structure:
{{
  "signal_side": "BUY" or "SELL" or "FLAT",
  "signal_confidence": 0.0 to 1.0,
  "reasoning": "A concise 1-sentence explanation of your decision citing specific metrics."
}}
"""
        logger.info("🧠 ReasoningService: Invoking LLM for logic synthesis...")

        # Construct Data Block for LLM Adapter
        data_block = f"""
Price: ${market.get("price", 0.0)}
News: {market.get("news_context", "None")}
Physics: Velocity={physics.get("velocity", 0.0):.4f}, Accel={physics.get("acceleration", 0.0):.4f}, Regime={physics.get("regime", "Unknown")}
Forecast: {forecast.get("trend", "Neutral")} (Conf: {forecast.get("confidence", 0.0)})
Sentiment: {sentiment.get("label", "Neutral")} (Score: {sentiment.get("score", 0.0)})
Quantum Interference: {interference:.4f}
"""

        # Set span attributes for observability
        span = trace.get_current_span()
        span.set_attribute("llm.model", "gemma2:9b")
        span.set_attribute("llm.prompt_type", "god_prompt")
        span.set_attribute("llm.symbol", market.get("symbol", "unknown"))

        # Time LLM inference
        start_time = time.time()
        # We pass data_block. If LLMAdapter expects prompts, we might need to change this,
        # but based on previous code it was passing formatted strings.
        # Ideally we pass 'prompt_text' if get_trade_signal supports direct prompt,
        # but looking at original code it seemed to use a helper.
        # I'll stick to data_block + implied system prompt in adapter, PLUS the manual Context if needed.
        # Actually, LLMAdapter likely wraps input.
        # For now I will pass data_block as before.
        result = self.llm.get_trade_signal(data_block)
        inference_time_ms = (time.time() - start_time) * 1000

        # Set output attributes
        signal_side = result.get("signal_side", "FLAT")
        signal_conf = result.get("signal_confidence", 0.0)
        span.set_attribute("llm.signal_side", signal_side)
        span.set_attribute("llm.signal_confidence", signal_conf)
        span.set_attribute("llm.inference_time_ms", inference_time_ms)

        # Record business metrics
        symbol = market.get("symbol", "unknown")
        business_metrics.signals_total.add(1, {"side": signal_side, "symbol": symbol})
        business_metrics.record_histogram_with_exemplar(
            business_metrics.signal_confidence,
            signal_conf,
            {"side": signal_side, "symbol": symbol},
        )
        business_metrics.record_histogram_with_exemplar(
            business_metrics.llm_inference_time,
            inference_time_ms,
            {"model": "gemma2:9b", "symbol": symbol},
        )

        return {
            "signal_side": signal_side,
            "signal_confidence": signal_conf,
            "reasoning": result.get("reasoning", "Analysis failed."),
        }

    @tracer.start_as_current_span("reasoning_arbitrate_tournament")
    def arbitrate_tournament(self, candidates: list) -> Dict[str, Any]:
        """
        The Tournament of Minds.
        Compares multiple Analysis Reports and selects the single best candidate.

        Args:
            candidates: List of dicts (full analysis reports).

        Returns:
            {
                "winner_symbol": str,
                "rationale": str
            }
        """
        if not candidates:
            return {"winner_symbol": None, "rationale": "No candidates to arbitrate."}

        # Filter out candidates with low confidence or bad physics automatically?
        # No, let the LLM see the "Board" and decide, but we highlight the risks.

        # 1. Format the Board
        board_text = ""
        for i, c in enumerate(candidates, 1):
            board_text += (
                f"Candidate {i}: {c.get('symbol')} | "
                f"Side: {c.get('signal_side')} (Conf: {c.get('signal_confidence', 0):.2f}) | "
                f"Phys: Vel={c.get('velocity', 0):.3f}, Acc={c.get('acceleration', 0):.3f}, "
                f"Regime={c.get('regime')} (α={c.get('current_alpha', 0):.2f}) | "
                f"Reason: {c.get('reasoning')}\n"
            )

        # 2. Construct the Chief Risk Officer Prompt
        prompt = f"""
You are the Chief Risk Officer (CRO). A set of trading candidates has been proposed by your analysts.
Your job is to run a TOURNAMENT to select the SINGLE BEST trade.

--- THE CANDIDATES ---
{board_text}
--- MISSION ---
Select the ONE winner based on:
1. Confluence: Does Physics + Forecast + Sentiment align?
2. Safety: Avoid 'Critical' regimes or infinite variance (Alpha < 1.7).
3. Clarity: Prefer high confidence signals with clear reasoning.

If NO candidate is safe or compelling, select "NONE".

--- OUTPUT FORMAT ---
Respond ONLY with this JSON:
{{
  "winner_symbol": "SYMBOL" or "NONE",
  "rationale": "Concise justification for why this candidate beat the others."
}}
"""
        logger.info(
            f"🧠 Reasoning: Starting Tournament with {len(candidates)} candidates."
        )

        # 3. Invoke LLM
        # We use a distinct prompt type for observability
        span = trace.get_current_span()
        span.set_attribute("llm.prompt_type", "tournament")

        start_time = time.time()
        result = self.llm.get_trade_signal(
            prompt
        )  # Re-using get_trade_signal as it returns JSON
        inference_time_ms = (time.time() - start_time) * 1000

        winner = result.get("winner_symbol")
        # Handle case where LLM returns "NONE" string vs None type
        if winner == "NONE":
            winner = None

        span.set_attribute("llm.tournament_winner", str(winner))

        business_metrics.record_histogram_with_exemplar(
            business_metrics.llm_inference_time,
            inference_time_ms,
            {"model": "gemma2:9b", "type": "tournament"},
        )

        return {
            "winner_symbol": winner,
            "rationale": result.get("rationale", "Tournament Concluded."),
        }
