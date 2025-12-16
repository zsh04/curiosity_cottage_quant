from typing import Dict, Any
import requests
import time
import logging
import os

logger = logging.getLogger(__name__)


class LLMAdapter:
    """Enhanced LLM Adapter with full observability for Gemma2/Ollama"""

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_API_URL", "http://ollama:11434")
        self.model = os.getenv("LLM_MODEL", "gemma2:9b")

    def get_trade_signal(self, context: str) -> Dict[str, Any]:
        """
        Query Gemma2 9B with full observability.

        Returns:
            dict with keys: signal_side, signal_confidence, reasoning,
                           raw_response, tokens_input, tokens_output, latency_ms
        """
        start = time.time()

        prompt = f"""You are a quantitative trading analyst. Based on the following market context, provide a trading signal.

CONTEXT:
{context}

Respond in this exact JSON format:
{{
  "signal_side": "BUY|SELL|FLAT",
  "signal_confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}
"""

        try:
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            raw_output = data.get("response", "{}")

            # Parse JSON response from LLM
            import json

            try:
                parsed = json.loads(raw_output)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM JSON: {raw_output}")
                parsed = {
                    "signal_side": "FLAT",
                    "signal_confidence": 0.0,
                    "reasoning": "Failed to parse LLM response",
                }

            latency_ms = (time.time() - start) * 1000

            # Approximate token counts
            tokens_in = len(prompt.split())
            tokens_out = len(raw_output.split())

            return {
                "signal_side": parsed.get("signal_side", "FLAT"),
                "signal_confidence": parsed.get("signal_confidence", 0.0),
                "reasoning": parsed.get("reasoning", "No reasoning provided"),
                "raw_response": raw_output,  # Full LLM output for observability
                "tokens_input": tokens_in,
                "tokens_output": tokens_out,
                "latency_ms": latency_ms,
            }

        except Exception as e:
            logger.error(f"LLM Error: {e}")
            latency_ms = (time.time() - start) * 1000

            # Return safe fallback
            return {
                "signal_side": "FLAT",
                "signal_confidence": 0.0,
                "reasoning": f"LLM Error: {str(e)}",
                "raw_response": "",
                "tokens_input": len(prompt.split()),
                "tokens_output": 0,
                "latency_ms": latency_ms,
                "error": str(e),
            }
