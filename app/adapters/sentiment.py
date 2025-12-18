"""
FinBERT Sentiment Analysis Adapter (Native Metal)
Performs local ONNX inference for financial sentiment classification.
Removes dependency on external container and leverages CPU/Neural Engine.
"""

import logging
import os
import time
import numpy as np
from typing import Dict, Any, List, Union
from opentelemetry import trace

# Try importing dependencies
try:
    import onnxruntime as ort
    from transformers import AutoTokenizer, pipeline

    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

try:
    from transformers import AutoTokenizer, pipeline, AutoModelForSequenceClassification

    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class SentimentAdapter:
    """
    Local Sentiment Adapter for FinBERT.

    Architecture:
        - Mode 1 (Preferred): ONNX Runtime (Native Metal/CPU) - Fastest (<50ms)
        - Mode 2 (Fallback): Transformers Pipeline (PyTorch) - If ONNX missing (Python 3.14+)
    """

    def __init__(self):
        """
        Initialize ONNX session or PyTorch pipeline.
        """
        self.model_path = os.path.join("models", "finbert_onnx", "model.onnx")
        self.tokenizer_path = os.path.join("models", "finbert_onnx")
        self.session = None
        self.tokenizer = None
        self.pipeline = None
        self.id2label = {0: "positive", 1: "negative", 2: "neutral"}  # FinBERT mapping
        self.mode = "OFFLINE"

        if HAS_ONNX and os.path.exists(self.model_path):
            self._init_onnx()
        elif HAS_TRANSFORMERS:
            self._init_pytorch()
        else:
            logger.warning(
                "SentimentAdapter: Missing 'onnxruntime' AND 'transformers'. Running in fallback mode."
            )

    def _init_onnx(self):
        try:
            logger.info(
                f"SentimentAdapter: Loading Native Metal Model from {self.model_path}..."
            )
            start_t = time.perf_counter()

            # Use CoreML for Apple Silicon, CPU fallback for others
            providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
            self.session = ort.InferenceSession(self.model_path, providers=providers)

            # Load Tokenizer using Transformers
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.tokenizer_path, local_files_only=True
            )

            load_time = (time.perf_counter() - start_t) * 1000
            logger.info(
                f"SentimentAdapter: ONNX Model Loaded in {load_time:.2f}ms. Providers: {self.session.get_providers()}"
            )
            self.mode = "ONNX"
        except Exception as e:
            logger.error(f"SentimentAdapter: ONNX Initialization failed: {e}")
            self.session = None
            # Try falling back to PyTorch if ONNX fails
            if HAS_TRANSFORMERS:
                logger.info("SentimentAdapter: Falling back to PyTorch...")
                self._init_pytorch()

    def _init_pytorch(self):
        """
        Fallback for when ONNX is unavailable (e.g. Python 3.14)
        """
        try:
            logger.info("SentimentAdapter: Initializing PyTorch Pipeline (Fallback)...")
            start_t = time.perf_counter()

            # Use 'ProsusAI/finbert' directly or from local cache if we had model files
            # Since we likely only have the ONNX export locally, we might need to fetch from hub again
            # OR try to load from the generic cache if available.
            # Ideally we download 'ProsusAI/finbert' once.

            model_name = "ProsusAI/finbert"
            self.pipeline = pipeline(
                "sentiment-analysis", model=model_name, tokenizer=model_name
            )

            load_time = (time.perf_counter() - start_t) * 1000
            logger.info(f"SentimentAdapter: PyTorch Model Loaded in {load_time:.2f}ms")
            self.mode = "PYTORCH"
        except Exception as e:
            logger.error(f"SentimentAdapter: PyTorch Initialization failed: {e}")
            self.pipeline = None

    def _softmax(self, x):
        """Compute softmax values for each set of scores in x."""
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()

    @tracer.start_as_current_span("finbert_analyze")
    def analyze(self, text: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Analyze sentiment using available backend.
        """
        if self.mode == "ONNX":
            return self._analyze_onnx(text)
        elif self.mode == "PYTORCH":
            return self._analyze_pytorch(text)
        else:
            return self._fallback_response("model_offline")

    def _analyze_onnx(self, text: Union[str, List[str]]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        span = trace.get_current_span()

        input_text = text if isinstance(text, str) else text[0]

        try:
            inputs = self.tokenizer(
                input_text,
                return_tensors="np",
                padding=True,
                truncation=True,
                max_length=512,
            )

            ort_inputs = {
                k: v
                for k, v in inputs.items()
                if k in [x.name for x in self.session.get_inputs()]
            }

            logits = self.session.run(None, ort_inputs)[0][0]
            probs = self._softmax(logits)
            pred_idx = np.argmax(probs)
            confidence = float(probs[pred_idx])
            sentiment = self.id2label.get(pred_idx, "neutral")

            latency_ms = (time.perf_counter() - start_time) * 1000

            return self._format_result(sentiment, confidence, latency_ms)

        except Exception as e:
            logger.error(f"SentimentAdapter: ONNX Inference failed: {e}")
            return self._fallback_response(str(e))

    def _analyze_pytorch(self, text: Union[str, List[str]]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        input_text = text if isinstance(text, str) else text[0]

        try:
            # Pipeline returns [{'label': 'positive', 'score': 0.9}]
            # FinBERT model output labels might be 'positive', 'negative', 'neutral' directly
            result = self.pipeline(input_text)[0]
            sentiment = result["label"].lower()
            confidence = float(result["score"])
            latency_ms = (time.perf_counter() - start_time) * 1000

            return self._format_result(sentiment, confidence, latency_ms)
        except Exception as e:
            logger.error(f"SentimentAdapter: PyTorch Inference failed: {e}")
            return self._fallback_response(str(e))

    def _format_result(self, sentiment, confidence, latency_ms):
        span = trace.get_current_span()
        span.set_attribute("finbert.sentiment", sentiment)
        span.set_attribute("finbert.score", confidence)
        span.set_attribute("finbert.backend", self.mode)

        return {
            "sentiment": sentiment,
            "label": sentiment,
            "score": confidence,
            "latency_ms": latency_ms,
            "backend": self.mode,
        }

    def _fallback_response(self, error_msg: str) -> Dict[str, Any]:
        return {
            "sentiment": "neutral",
            "label": "neutral",
            "score": 0.0,
            "latency_ms": 0,
            "error": error_msg,
        }

    def health_check(self) -> bool:
        return self.mode != "OFFLINE"
