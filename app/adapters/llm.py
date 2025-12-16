from typing import Dict, Any


class LLMAdapter:
    @staticmethod
    def get_trade_signal(prompt: str) -> Dict[str, Any]:
        # TODO: Implement actual LLM call (e.g. Ollama/DeepSeek)
        # Expected to return JSON structure matching requirements
        return {
            "signal_side": "FLAT",
            "signal_confidence": 0.5,
            "reasoning": "Market is choppy, velocity is low. Staying flat.",
        }
