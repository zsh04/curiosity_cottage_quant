import logging
from typing import List
from datetime import datetime

from pydantic_ai.models import (
    Model,
    ModelRequestParameters,
    ModelSettings,
)
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ModelRequest,
    UserPromptPart,
    SystemPromptPart,
)

logger = logging.getLogger(__name__)


class MLXModel(Model):
    """
    Adapter for running MLX-LM models (Gemma 2) natively on Apple Silicon
    within the PydanticAI framework.
    """

    def __init__(self, model_name: str = "google/gemma-2-9b-it"):
        self._model_name = model_name
        self.max_tokens = 1000
        self.temp = 0.7

    async def request(
        self,
        messages: List[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """
        Execute request via standard mlx_lm generation.
        """
        try:
            # 1. Load Model (Cached via Factory)
            # This handles the heavy lifting of loading weights
            from app.agent.models_legacy import model_factory

            model, tokenizer = model_factory.load_gemma()

            if model == "MOCK_MODEL":
                return self._mock_response()

            # 2. Apply Chat Template
            # Convert PydanticAI messages to HF Chat format
            chat_messages = self._convert_messages(messages)

            prompt = tokenizer.apply_chat_template(
                chat_messages, tokenize=False, add_generation_prompt=True
            )

            # 3. Generate (Blocking Call - needs to be optimized for Async if possible,
            # but MLX is mostly synchronous on the metal. We run in thread if needed,
            # but PydanticAI 'request' is async, so we can await if we wrapper it.)
            # For now, running sync in this async method.

            from mlx_lm import generate

            # Extract params
            max_t = self.max_tokens
            temp = self.temp
            if model_settings:
                max_t = model_settings.get("max_tokens", max_t)
                temp = model_settings.get("temperature", temp)

            response_text = generate(
                model,
                tokenizer,
                prompt=prompt,
                verbose=False,
                max_tokens=max_t,
                temp=temp,
            )

            # 4. Construct Response
            return ModelResponse(
                parts=[TextPart(content=response_text)],
                model_name=self._model_name,
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"MLX Inference Failed: {e}")
            raise e

    def _convert_messages(self, messages: List[ModelMessage]) -> List[dict]:
        """Convert internal schema to HuggingFace Chat Template."""
        hf_msgs = []
        for msg in messages:
            if isinstance(msg, ModelRequest):
                # PydanticAI calls the 'developer' part inputs 'system' usually in parts?
                # Actually ModelRequest usually contains User info.
                # Let's inspect parts.
                content = ""
                role = "user"

                for part in msg.parts:
                    if isinstance(part, SystemPromptPart):
                        role = "system"
                        content += part.content
                    elif isinstance(part, UserPromptPart):
                        role = "user"
                        content += part.content
                    elif isinstance(part, TextPart):
                        content += part.content

                if content:
                    hf_msgs.append({"role": role, "content": content})

        return hf_msgs

    def _mock_response(self) -> ModelResponse:
        """Fallback for non-Silicon environments."""
        mock_json = """
        {
            "action": "HOLD",
            "confidence": 0.5,
            "reasoning": "Mock Execution (MLX not available)."
        }
        """
        return ModelResponse(
            parts=[TextPart(content=mock_json)],
            model_name="mock-gemma",
            timestamp=datetime.now(),
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def system(self) -> str:
        return "mlx"
