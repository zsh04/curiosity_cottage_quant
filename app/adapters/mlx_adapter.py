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
    """PydanticAI adapter for MLX-LM (Gemma 2 9B) on Apple Silicon.

    Runs Gemma 2 natively on MPS (Apple Metal) via MLX framework for structured
    reasoning without external API calls. Integrates with PydanticAI for type-safe
    LLM responses.

    **Architecture**:
    - **Model**: google/gemma-2-9b-it (instruction-tuned)
    - **Runtime**: MLX (Apple Silicon optimized)
    - **Framework**: PydanticAI (structured outputs)
    - **Fallback**: Mock responses in non-Silicon environments

    **Performance**:
    - M1/M2/M3: ~500ms-2s per generation (1000 tokens)
    - Memory: ~9GB VRAM (quantized: ~5GB)

    **Safety**:
    - PROD mode: Raises error if MLX unavailable (no mock trading)
    - DEV mode: Returns mock JSON for testing

    Example:
        >>> model = MLXModel("google/gemma-2-9b-it")
        >>> response = await model.request(messages, settings, params)
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
            from app.agent.models_legacy import model_factory
            from app.core.config import settings

            model, tokenizer = model_factory.load_gemma()

            # CRITICAL: No mock fallback in production
            if model == "MOCK_MODEL":
                if settings.ENV == "PROD":
                    raise RuntimeError(
                        "❌ CRITICAL: MLX model unavailable in PRODUCTION mode. "
                        "Cannot execute live trading on mock data. "
                        "Install MLX and Gemma weights, or switch to DEV environment."
                    )
                else:
                    logger.warning("⚠️ DEV MODE: Using mock MLX response (testing only)")
                    return self._mock_response()

            # 2. Apply Chat Template
            chat_messages = self._convert_messages(messages)

            prompt = tokenizer.apply_chat_template(
                chat_messages, tokenize=False, add_generation_prompt=True
            )

            # 3. Generate
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
