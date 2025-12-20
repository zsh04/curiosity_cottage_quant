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
        from app.core.config import settings
        from concurrent.futures import ThreadPoolExecutor

        self.mode = "LOCAL"  # Force Local Mode (Gemini Rolled Back)
        self.llm = LLMAdapter()  # Default Local

        # Async Background Brain (Local Fallback)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.pending_tasks: Dict[str, Any] = {}  # Map 'task_id' -> Future

        logger.info(f"🧠 ReasoningService initialized in {self.mode} mode.")

    def submit_local_tournament(self, candidates: list) -> str:
        """
        Submit a Local LLM Tournament task to the background executor.
        Returns a 'task_id' (e.g. 'tournament_TICK_X').
        """
        task_id = f"tournament_{int(time.time())}"

        # Guard: Only one pending tournament at a time to avoid queue buildup
        # Clear old tasks if any
        self.pending_tasks.clear()

        logger.info(
            f"ReasoningService: Submitting BACKGROUND Local Tournament ({task_id})"
        )

        # This function runs in the thread
        def _run_tournament(cands):
            # Construct Prompt (Duplicated logic from arbitrate_tournament, refactor ideally)
            # For simplicity, we call the LOCAL logic directly here.
            # We need to construct the prompt string inside the thread or pass it?
            # Let's pass the prompt generation logic.

            # 1. Format Board
            board_text = ""
            for i, c in enumerate(cands, 1):
                board_text += (
                    f"Candidate {i}: {c.get('symbol')} | "
                    f"Side: {c.get('signal_side')} (Conf: {c.get('signal_confidence', 0):.2f}) | "
                    f"Phys: Vel={c.get('velocity', 0):.3f}, Acc={c.get('acceleration', 0):.3f}, "
                    f"Regime={c.get('regime')} (α={c.get('current_alpha', 0):.2f}) | "
                    f"Reason: {c.get('reasoning')}\n"
                )

            prompt = f"""
You are the Chief Risk Officer (CRO). Run a TOURNAMENT to select the SINGLE BEST trade.
--- CANDIDATES ---
{board_text}
--- MISSION ---
Select ONE winner. Output JSON: {{ "winner_symbol": "SYMBOL" or "NONE", "rationale": "reason" }}
"""
            # Local Inference (Blocking in this thread)
            raw = self.llm.infer(prompt)
            return raw

        # Submit
        future = self.executor.submit(_run_tournament, candidates)
        self.pending_tasks[task_id] = future
        return task_id

    def check_background_result(self) -> Dict[str, Any]:
        """
        Check if the unique background task has completed.
        Returns result dict if ready, else None.
        """
        if not self.pending_tasks:
            return None

        # Get the latest task (we only keep one active really)
        task_id, future = next(iter(self.pending_tasks.items()))

        if future.done():
            try:
                raw = future.result()
                # Clear task
                del self.pending_tasks[task_id]

                # Parse
                import json

                try:
                    cleaned = (
                        raw.strip().replace("```json", "").replace("```", "").strip()
                    )
                    result = json.loads(cleaned)
                    result["source"] = "BACKGROUND_LOCAL"
                    return result
                except:
                    return {
                        "winner_symbol": None,
                        "rationale": "Background Local Parse Error",
                    }

            except Exception as e:
                logger.error(f"Background Brain Failed: {e}")
                del self.pending_tasks[task_id]
                business_metrics.llm_errors.add(1, {"source": "background_brain"})
                return None

        return None

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
        Synthesizes multi-modal data into a decision.
        """
        # Unpack Context for Prompt Construction
        market = context.get("market", {})
        physics = context.get("physics", {})
        forecast = context.get("forecast", {})
        sentiment = context.get("sentiment", {})

        # --- QUANTUM SENTIMENT ANALYSIS ---
        recent_news = market.get("recent_news", [])
        if len(recent_news) >= 2:
            news_A = recent_news[0]
            news_B = recent_news[1]
            interference = self.calculate_interference(news_A, news_B)
        elif len(recent_news) == 1:
            interference = self.calculate_interference(recent_news[0], recent_news[0])
        else:
            interference = 0.0

        logger.info(
            f"🧠 ReasoningService: Invoking {self.mode} LLM for logic synthesis..."
        )

        # Construct Data Block for LLM Adapter
        data_block = f"""
Price: ${market.get("price", 0.0)}
News: {market.get("news_context", "None")}
Physics: Velocity={physics.get("velocity", 0.0):.4f}, Accel={physics.get("acceleration", 0.0):.4f}, Regime={physics.get("regime", "Unknown")}
Forecast: {forecast.get("trend", "Neutral")} (Conf: {forecast.get("confidence", 0.0)})
Sentiment: {sentiment.get("label", "Neutral")} (Score: {sentiment.get("score", 0.0)})
Quantum Interference: {interference:.4f}
"""

        start_time = time.time()
        result = None

        # --- LOCAL ONLY LOGIC ---
        result = self.llm.get_trade_signal(data_block)

        inference_time_ms = (time.time() - start_time) * 1000

        # Set output attributes
        signal_side = result.get("signal_side", "FLAT")
        signal_conf = result.get("signal_confidence", 0.0)

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
            {"model": self.mode, "symbol": symbol},
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
        """
        if not candidates:
            return {"winner_symbol": None, "rationale": "No candidates to arbitrate."}

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
            f"🧠 Reasoning: Starting {self.mode} Tournament with {len(candidates)} candidates."
        )

        start_time = time.time()

        # --- LOCAL LOGIC ONLY (Cloud Removed) ---
        # --- LOCAL LOGIC ONLY (Cloud Removed) ---
        raw = self.llm.infer(prompt)
        try:
            import json
            import re

            # Robust Regex Extraction
            # matches { ... } including nested braces
            # Simplest valid approach for this use case: find first { and last }
            match = re.search(r"\{.*\}", raw.replace("\n", " "), re.DOTALL)
            if match:
                json_str = match.group(0)
                result = json.loads(json_str)
            else:
                raise ValueError("No JSON found")

        except Exception as e:
            logger.warning(f"RISK: LLM Parse Error: {e} | Raw: {raw[:100]}...")
            result = {"winner_symbol": None, "rationale": f"Local Parse Error ({e})"}

        inference_time_ms = (time.time() - start_time) * 1000

        winner = result.get("winner_symbol")
        if winner == "NONE":
            winner = None

        business_metrics.record_histogram_with_exemplar(
            business_metrics.llm_inference_time,
            inference_time_ms,
            {"model": self.mode, "type": "tournament"},
        )

        return {
            "winner_symbol": winner,
            "rationale": result.get("rationale", "Tournament Concluded."),
        }


# Singleton Instance
_reasoning_service_instance = None


def get_reasoning_service() -> ReasoningService:
    global _reasoning_service_instance
    if _reasoning_service_instance is None:
        _reasoning_service_instance = ReasoningService()
    return _reasoning_service_instance
