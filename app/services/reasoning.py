from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import Dict, Any, Literal
import logging
import time
import math
import os
import orjson
from opentelemetry import trace
from app.core import metrics as business_metrics

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# --- Structured Output Model ---
class TradeDecision(BaseModel):
    """
    The formal decision output from the Chief Risk Officer (LLM).
    """

    action: Literal["BUY", "SELL", "HOLD"] = Field(
        ..., description="The trading action to take."
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)."
    )
    reasoning: str = Field(
        ...,
        description="Concise justification for the decision, citing specific signals.",
    )
    # Optional advanced fields
    stop_loss: float | None = Field(
        default=None, description="Suggested stop loss price."
    )
    take_profit: float | None = Field(
        default=None, description="Suggested take profit price."
    )


class ReasoningService:
    """
    Reasoning Service: The 'Prefrontal Cortex' of the system.
    Synthesizes multi-modal data using Pydantic AI for structured reasoning.
    """

    def __init__(self):
        from concurrent.futures import ThreadPoolExecutor

        self.mode = "LOCAL"
        model_name = os.getenv("OLLAMA_MODEL", "llama3.1")

        # Pydantic AI Agent
        # Uses 'ollama:model_name' implicitly if configured, or we specify explicitly.
        # Assuming we use a generic provider or the user has pydantic-ai configured for Ollama.
        # For now, using standard 'ollama:...' string if supported, or just 'openai:...' if via OpenAI compat.
        # The user's prompt implies 'ollama' model.
        # Let's assume standard 'ollama:llama3.1'.

        try:
            # Platform Check for Silicon Handshake
            import platform

            processor = platform.processor()
            is_silicon = "arm" in processor.lower() if processor else False

            # Check if user explicitly forced Ollama via env
            force_ollama = os.getenv("FORCE_OLLAMA", "false").lower() == "true"

            if is_silicon and not force_ollama:
                # 🍏 Apple Silicon Path: Native MLX
                logger.info(
                    "🍏 Apple Silicon Detected. Engaging Quantum Holodeck (MLX Native)."
                )
                from app.adapters.mlx_adapter import MLXModel

                # Use "google/gemma-2-9b-it" which matches the legacy loader key
                model_adapter = MLXModel(model_name="google/gemma-2-9b-it")
                self.agent = Agent(
                    model_adapter,
                    output_type=TradeDecision,
                    system_prompt="You are the Chief Risk Officer (CRO) of a quantitative hedge fund. Analyze the data and make a trading decision.",
                )
                self.mode = "MLX_NATIVE"
            else:
                # 🐧 Linux/Cloud Path: Ollama Fallback
                logger.info(f"☁️ Using Ollama Bridge (Model: {model_name})")
                self.agent = Agent(
                    f"ollama:{model_name}",
                    output_type=TradeDecision,
                    system_prompt="You are the Chief Risk Officer (CRO) of a quantitative hedge fund. Analyze the data and make a trading decision.",
                )
                self.mode = "OLLAMA_BRIDGE"

            logger.info(f"🧠 ReasoningService initialized (Mode: {self.mode})")
        except Exception as eobj:
            logger.warning(
                f"Failed to init Pydantic AI Agent: {eobj}. Fallback logic may be needed."
            )
            self.agent = None

        # Async Background Brain (Local Fallback for Tournament)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.pending_tasks: Dict[str, Any] = {}

    async def generate_signal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        The "God Prompt" Execution via Pydantic AI.
        """
        # Unpack Context
        market = context.get("market", {})
        physics = context.get("physics", {})
        forecast = context.get("forecast", {})
        sentiment = context.get("sentiment", {})
        strategies = context.get("strategies", {})

        # Quantum Interference
        recent_news = market.get("recent_news", [])
        if len(recent_news) >= 2:
            news_A = recent_news[0]
            news_B = recent_news[1]
            interference = self.calculate_interference(news_A, news_B)
        elif len(recent_news) == 1:
            interference = self.calculate_interference(recent_news[0], recent_news[0])
        else:
            interference = 0.0

        # Construct Context Dictionary
        context = {
            "price": market.get("price", 0.0),
            "news": market.get("news_context", "None"),
            "physics": {
                "velocity": physics.get("velocity", 0.0),
                "acceleration": physics.get("acceleration", 0.0),
                "regime": physics.get("regime", "Unknown"),
            },
            "forecast": {
                "trend": forecast.get("trend", "Neutral"),
                "confidence": forecast.get("confidence", 0.0),
            },
            "sentiment": {
                "label": sentiment.get("label", "Neutral"),
                "score": sentiment.get("score", 0.0),
            },
            "quantum_interference": float(interference),
            "council_signals": strategies,
        }

        # Serialize using orjson for speed and strict JSON compliance
        # This helps LLMs parse the input structure more reliably than arbitrary f-strings
        context_json = orjson.dumps(context).decode("utf-8")

        prompt = f"""
Analyze this market context and provide a Trade Decision.

CONTEXT:
{context_json}

INSTRUCTIONS:
- Analyze all signals in the JSON.
- If 'council_signals' contains aligning high-quality strategies (Kalman/Fractal), boost confidence.
- Warning if 'MoonPhase' contradicts.
- Return valid JSON TradeDecision.
"""
        start_time = time.time()

        try:
            if self.agent:
                # Run Pydantic AI
                # Note: run is async
                result = await self.agent.run(prompt)
                logger.info(f"DEBUG: Agent Run returned type: {type(result)}")
                decision = result.data  # TradeDecision object

                signal_side = decision.action
                signal_conf = decision.confidence
                reasoning = decision.reasoning
            else:
                # Fallback if agent init failed
                signal_side = "HOLD"
                signal_conf = 0.0
                reasoning = "Agent initialization failed."

        except Exception as e:
            logger.error(f"Reasoning Inference Failed: {e}")
            signal_side = "HOLD"
            signal_conf = 0.0
            reasoning = f"Error: {str(e)}"

        inference_time_ms = (time.time() - start_time) * 1000

        # Record Metrics
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
            "reasoning": reasoning,
        }

    def calculate_interference(
        self, news_A: Dict[str, Any], news_B: Dict[str, Any]
    ) -> float:
        """
        Calculate Quantum Interference between two news signals.
        """
        try:

            def sigmoid(x):
                return 1 / (1 + math.exp(-x))

            score_A = news_A.get("score", 0.0)
            score_B = news_B.get("score", 0.0)

            P_A = sigmoid(score_A)
            P_B = sigmoid(score_B)

            theta = abs(score_A - score_B) * math.pi
            interference = 2 * math.sqrt(P_A * P_B) * math.cos(theta)

            return float(interference)
        except Exception as e:
            logger.error(f"Quantum Interference calc failed: {e}")
            return 0.0

    # ... (Tournament logic can remain or be updated similarly later) ...
    # For now, keeping legacy tournament stub or removing if unused.
    # User focused on "generate_signal". I will keep arbitrate_tournament as a stub/legacy to avoid breaking interfaces if called.

    def arbitrate_tournament(self, candidates: list) -> Dict[str, Any]:
        return {
            "winner_symbol": None,
            "rationale": "Tournament Logic Pending Migration to Pydantic AI",
        }

    def check_background_result(self) -> Dict[str, Any] | None:
        """
        Check if any background optimization/tournament tasks have completed.
        Returns the result if ready, else None.
        """
        keys_to_remove = []
        result = None

        for task_id, future in self.pending_tasks.items():
            if future.done():
                try:
                    result = future.result()
                    keys_to_remove.append(task_id)
                    # For now only return the first completed one
                    break
                except Exception as e:
                    logger.error(f"Background Task {task_id} failed: {e}")
                    keys_to_remove.append(task_id)

        for k in keys_to_remove:
            self.pending_tasks.pop(k, None)

        return result


# Singleton Instance
_reasoning_service_instance = None


def get_reasoning_service() -> ReasoningService:
    global _reasoning_service_instance
    if _reasoning_service_instance is None:
        _reasoning_service_instance = ReasoningService()
    return _reasoning_service_instance
