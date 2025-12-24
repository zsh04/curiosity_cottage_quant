import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SentimentAdapter:
    """FinBERT sentiment analyzer with ONNX Runtime acceleration.

    Classifies financial text as positive/negative/neutral using ProsusAI's FinBERT
    fine-tuned on financial news. Optimized via ONNX for CPU inference (~50-100ms).

    **Architecture**:
    - **Model**: ProsusAI/finbert (BERT-base fine-tuned on financial corpus)
    - **Runtime**: ONNX Runtime (via Optimum) → fallback to PyTorch
    - **Input**: Text (max 512 tokens, auto-truncated)
    - **Output**: {"label": "positive"|"negative"|"neutral", "score": float}

    **Performance**:
    - ONNX: ~50-100ms per headline
    - PyTorch: ~200-500ms per headline

    Example:
        >>> analyzer = SentimentAdapter()
        >>> result = analyzer.analyze("Fed signals dovish pivot")
        >>> print(result)  # {"label": "positive", "score": 0.87}
    """

    def __init__(self):
        try:
            # Use Optimum for ONNX Runtime acceleration
            from optimum.pipelines import pipeline

            # export=True will export the model to ONNX if not already present
            self.pipe = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                accelerator="ort",
                return_all_scores=True,
            )
            logger.info("🧠 SentimentAdapter: FinBERT Loaded (ONNX Runtime).")
        except Exception as e:
            logger.error(f"SentimentAdapter: Failed to load FinBERT (ONNX): {e}")
            # Fallback to standard transformers if Optimum fails
            try:
                from transformers import pipeline

                self.pipe = pipeline(
                    "text-classification",
                    model="ProsusAI/finbert",
                    return_all_scores=True,
                )
                logger.warning("⚠️ SentimentAdapter: Fallback to PyTorch (Slow).")
            except Exception as e2:
                logger.error(f"SentimentAdapter: CRITICAL FAILURE: {e2}")
                self.pipe = None

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text.
        Returns: { "label": "positive"|"negative"|"neutral", "score": float }
        """
        if not self.pipe:
            return {"label": "neutral", "score": 0.0}

        try:
            # Truncate text to avoid token limits (approx)
            truncated_text = text[:512]
            results = self.pipe(truncated_text)
            # results is [[{'label': 'positive', 'score': 0.9}, ...]]

            # Find max score
            scores = results[0]
            top_score = max(scores, key=lambda x: x["score"])

            return {"label": top_score["label"], "score": top_score["score"]}
        except Exception as e:
            logger.error(f"SentimentAdapter: Inference failed: {e}")
            return {"label": "neutral", "score": 0.0}
