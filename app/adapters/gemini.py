import google.generativeai as genai
from app.core.config import settings
import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class GeminiAdapter:
    """
    Adapter for Google's Gemini Models via Generative AI SDK.
    Acts as the Cloud Reasoning Engine.
    """

    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        if not self.api_key:
            logger.warning(
                "GeminiAdapter: No GOOGLE_API_KEY found. Cloud inference will fail."
            )
        else:
            genai.configure(api_key=self.api_key)

        # Initialize Model (Gemini 1.5 Pro or similar available tier)
        # Initialize Model (User Requested)
        self.model_name = "models/gemini-3-pro-preview"
        self.model = None

    def _ensure_model(self):
        if not self.model and self.api_key:
            try:
                self.model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                logger.error(
                    f"GeminiAdapter: Failed to initialize model {self.model_name}: {e}"
                )

    def generate_content(self, prompt: str) -> Optional[str]:
        """
        Synchronous generation.
        Returns text content or None on failure.
        """
        self._ensure_model()
        if not self.model:
            logger.error("GeminiAdapter: Model not initialized.")
            return None

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"GeminiAdapter: Generation failed: {e}")
            return None

    def get_trade_signal(self, context: str) -> Dict[str, Any]:
        """
        Generate trading signal using Gemini with structured output.
        Matches LLMAdapter interface.
        """
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
        raw_response = self.generate_content(prompt)

        if not raw_response:
            return {
                "signal_side": "FLAT",
                "signal_confidence": 0.0,
                "reasoning": "Gemini service unavailable",
                "raw_response": "",
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
        except Exception as e:
            logger.warning(
                f"GeminiAdapter: Failed to parse JSON: {raw_response[:100]} Error: {e}"
            )
            parsed = {
                "signal_side": "FLAT",
                "signal_confidence": 0.0,
                "reasoning": "Failed to parse Gemini response",
            }

        return {
            "signal_side": parsed.get("signal_side", "FLAT"),
            "signal_confidence": float(parsed.get("signal_confidence", 0.0)),
            "reasoning": parsed.get("reasoning", "No reasoning provided"),
            "raw_response": raw_response,
        }
