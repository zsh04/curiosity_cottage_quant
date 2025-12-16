from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
# For Chronos-Bolt, it might be AutoModelForCausalLM or specific pipeline.
# Standard Chronos (original) uses T5 (Seq2Seq).
# Chronos-Bolt (https://huggingface.co/amazon/chronos-bolt-small) is T5 based?
# "Chronos-Bolt models... are based on T5". Yes.
# Actually, the README says: pipeline("forecasting", model="amazon/chronos-bolt-small", device=device)
# But "forecasting" pipeline is not standard transformers yet unless specific version or library.
# The user linked HuggingFace page. Standard usage:
# from chronos import ChronosPipeline
# ... pipeline = ChronosPipeline.from_pretrained(...)
# But `chronos` library might be heavy.
# Let's try to use AutoModel if possible, but Chronos logic involves tokenizing time series values which is custom.
# Better to use the library provided or replicate.
# Creating a simple wrapper using `chronos` package if available, else assuming we install `git+https://github.com/amazon-science/chronos-forecasting.git`.
# Wait, I didn't add git to requirements.
# Let's use `transformers` generic load if possible, OR just try to assume standard usage.
# For now, I will write code that attempts to standard load.
# "amazon/chronos-bolt-small"

# "We recommend using the ChronosPipeline from the git repo".
# Okay, I will add git install to Dockerfile.

app = FastAPI(title="Chronos Forecasting Service")
pipeline_model = None


@app.on_event("startup")
def load_model():
    global pipeline_model
    try:
        # We will install the package in Dockerfile
        from chronos import ChronosPipeline

        device = "cpu"  # Force CPU for Mac compatibility
        if torch.cuda.is_available():
            device = "cuda"

        print(f"Loading Chronos-T5 (Chronos-2) on {device}...")
        pipeline_model = ChronosPipeline.from_pretrained(
            "amazon/chronos-t5-small",
            device_map=device,
            torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        )
        print("Chronos loaded.")
    except Exception as e:
        print(f"Failed to load Chronos: {e}")
        # raise e


class ForecastRequest(BaseModel):
    context: List[float]  # Historical values
    prediction_length: int = 12


class ForecastResponse(BaseModel):
    forecast: List[List[float]]  # Samples x Horizon (or Quantiles)
    # Chronos returns samples usually.


@app.get("/health")
def health():
    if pipeline_model is None:
        raise HTTPException(status_code=503, detail="Model Loading")
    return {"status": "ok"}


@app.post("/forecast")
def forecast(req: ForecastRequest):
    if not pipeline_model:
        raise HTTPException(status_code=503, detail="Model Loading")

    # context must be tensor
    context_tensor = torch.tensor(req.context)

    # predict
    forecast = pipeline_model.predict(
        context_tensor,
        prediction_length=req.prediction_length,
        num_samples=20,
    )
    # forecast shape: (1, num_samples, prediction_length)
    # return simple list
    return {"forecast": forecast[0].tolist()}
