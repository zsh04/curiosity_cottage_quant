from mlx_lm import load, generate
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
# import torch # Removed unused


class ModelFactory:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelFactory, cls).__new__(cls)
            cls._instance.models = {}
        return cls._instance

    def load_gemma(self):
        """Loads Gemma 2 (9B) via MLX-LM."""
        if "gemma" not in self.models:
            print("Loading Gemma 2 (9B) via MLX...")
            # Note: This requires the model to be downloaded.
            # First run might be slow.
            model, tokenizer = load("google/gemma-2-9b-it")
            self.models["gemma"] = (model, tokenizer)
            print("Gemma 2 Loaded.")
        return self.models["gemma"]

    def load_chronos(self):
        """Loads Chronos-Bolt via Transformers."""
        if "chronos" not in self.models:
            print("Loading Chronos-Bolt...")
            model = AutoModelForSeq2SeqLM.from_pretrained("amazon/chronos-bolt-base")
            tokenizer = AutoTokenizer.from_pretrained("amazon/chronos-bolt-base")
            self.models["chronos"] = (model, tokenizer)
            print("Chronos-Bolt Loaded.")
        return self.models["chronos"]

    def load_finbert(self):
        """Loads FinBERT via Transformers Pipeline."""
        if "finbert" not in self.models:
            print("Loading FinBERT...")
            pipe = pipeline(
                "text-classification", model="ProsusAI/finbert", return_all_scores=True
            )
            self.models["finbert"] = pipe
            print("FinBERT Loaded.")
        return self.models["finbert"]

    def generate_thought(self, prompt: str) -> str:
        """
        Generates reasoning using Gemma 2.
        """
        # TEMP FIX: Bypass model load due to GatedRepoError/Missing Auth
        # model, tokenizer = self.load_gemma()
        # response = generate(model, tokenizer, prompt=prompt, verbose=True)
        return "Comparison: BULLISH (Mocked Thought)"

    def forecast_series(self, context_tensor):
        """
        Forecasts using Chronos.
        """
        # TEMP FIX: Bypass model load due to sentencepiece/py3.14 bug
        # model, tokenizer = self.load_chronos()
        # Mock forecast logic for now as tensor prep is complex
        # prediction = model.generate(context_tensor)
        return "[Chronos Forecast Data: BULLISH TREND PREDICTED]"

    def analyze_sentiment(self, text: str):
        """
        Scores sentiment using FinBERT.
        """
        pipe = self.load_finbert()
        return pipe(text)


model_factory = ModelFactory()
