"""
LLM Adapter for Gemma2 (Ollama)
Connects to cc_brain for local language model inference.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

import requests
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class LLMAdapter:
    """
    Client for Gemma2 9B running on Ollama.

    Ollama provides:
        - Local LLM inference (no API costs)
        - Fast response times
        - Full control over prompt engineering
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LLM adapter.

        Args:
            base_url: Ollama service URL (defaults to settings or http://cc_brain:11434)
            model: Model name (defaults to settings or gemma2:9b)
        """
        from app.core.config import settings

        self.base_url = (
            base_url
            or getattr(settings, "OLLAMA_BASE_URL", None)
            or os.getenv("OLLAMA_BASE_URL", "http://cc_brain:11434")
        )
        self.model = (
            model
            or os.getenv("OLLAMA_MODEL", None)  # Prioritize OLLAMA_MODEL env var
            or getattr(settings, "LLM_MODEL", None)
            or os.getenv("LLM_MODEL", "gemma2:9b")
        )
        self.timeout = 120.0  # Increased to 120s for local inference lag

    @tracer.start_as_current_span("llm_infer")
    def infer(
        self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.1
    ) -> str:
        """
        Generate text completion using Ollama.

        Args:
            prompt: User prompt/query
            system_prompt: Optional system prompt for behavior control
            temperature: Sampling temperature (0.0=deterministic, 1.0=creative)

        Returns:
            str: Raw LLM response text
            Returns empty string on error
        """
        span = trace.get_current_span()
        span.set_attribute("llm.model", self.model)
        span.set_attribute("llm.temperature", temperature)
        span.set_attribute("llm.prompt_length", len(prompt))

        try:
            # Construct payload for Ollama API
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }

            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt
                span.set_attribute("llm.has_system_prompt", True)

            # POST to Ollama generate endpoint
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                logger.error(
                    f"Ollama error: HTTP {response.status_code} - {response.text}"
                )
                span.set_attribute("error", True)
                return ""

            # Parse response
            data = response.json()
            raw_response = data.get("response", "")

            # Extract token counts if available
            eval_count = data.get("eval_count", 0)  # Output tokens
            prompt_eval_count = data.get("prompt_eval_count", 0)  # Input tokens

            span.set_attribute("llm.tokens_input", prompt_eval_count)
            span.set_attribute("llm.tokens_output", eval_count)
            span.set_attribute("llm.response_length", len(raw_response))

            logger.debug(
                f"🧠 LLM: Generated {eval_count} tokens "
                f"(input: {prompt_eval_count}, temp: {temperature})"
            )

            return raw_response

        except requests.Timeout:
            logger.warning(f"⏱️  LLM timeout after {self.timeout}s")
            span.set_attribute("error.timeout", True)
            return ""

        except requests.ConnectionError:
            logger.warning("🔌 Ollama service unreachable (cc_brain down?)")
            span.set_attribute("error.connection", True)
            return ""

        except Exception as e:
            logger.error(f"LLM adapter error: {e}")
            span.set_attribute("error", True)
            return ""

    def get_trade_signal(self, context: str) -> Dict[str, Any]:
        """
        Generate trading signal using LLM with structured output.

        Args:
            context: Market context string (price, velocity, acceleration, etc.)

        Returns:
            Dict with keys:
                - signal_side: "BUY" | "SELL" | "FLAT"
                - signal_confidence: float (0.0-1.0)
                - reasoning: str
                - raw_response: str (full LLM output)
                - tokens_input: int
                - tokens_output: int
        """
        system_prompt = "You are a quantitative trading analyst. Provide concise, actionable trading signals."

        prompt = f"""Based on the following market context, provide a trading signal.

CONTEXT:
{context}

Respond in this exact JSON format:
{{
  "signal_side": "BUY|SELL|FLAT",
  "signal_confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}
"""

        # Get raw response
        raw_response = self.infer(prompt, system_prompt=system_prompt, temperature=0.1)

        if not raw_response:
            # LLM failed, return safe fallback
            return {
                "signal_side": "FLAT",
                "signal_confidence": 0.0,
                "reasoning": "LLM service unavailable",
                "raw_response": "",
                "tokens_input": 0,
                "tokens_output": 0,
            }

        # Parse JSON response
        try:
            # Clean up markdown code blocks if present
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```"):
                cleaned_response = (
                    cleaned_response.replace("```json", "").replace("```", "").strip()
                )

            parsed = json.loads(cleaned_response)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM JSON: {raw_response[:100]}")
            parsed = {
                "signal_side": "FLAT",
                "signal_confidence": 0.0,
                "reasoning": "Failed to parse LLM response",
            }

        # Approximate token counts (Ollama provides exact counts in infer method)
        tokens_in = len(prompt.split())
        tokens_out = len(raw_response.split())

        return {
            "signal_side": parsed.get("signal_side", "FLAT"),
            "signal_confidence": float(parsed.get("signal_confidence", 0.0)),
            "reasoning": parsed.get("reasoning", "No reasoning provided"),
            "raw_response": raw_response,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
        }

    def health_check(self) -> bool:
        """
        Check if Ollama service is healthy.

        Returns:
            True if service is running and model is loaded
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2.0)
            if response.status_code == 200:
                # Check if our model is available
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                return self.model in models
            return False
        except Exception:
            return False
