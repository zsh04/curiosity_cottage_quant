from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

app = FastAPI(title="FinBERT Sentiment Service")

# Load model globally (startup)
# Using ProsusAI/finbert is standard for financial sentiment
MODEL_NAME = "ProsusAI/finbert"
classifier = None


@app.on_event("startup")
def load_model():
    global classifier
    print(f"Loading {MODEL_NAME}...")
    try:
        classifier = pipeline(
            "sentiment-analysis", model=MODEL_NAME, device=-1
        )  # CPU for now unless CUDA available in container
        # Note: In container with GPU, device=0. But let's let pipeline auto-detect or default to CPU for safety.
        # Actually pipeline("...", device=0) if torch.cuda.is_available() else -1
        import torch

        device = 0 if torch.cuda.is_available() else -1
        classifier = pipeline("sentiment-analysis", model=MODEL_NAME, device=device)
        print(f"Model loaded on device {device}")
    except Exception as e:
        print(f"Failed to load model: {e}")
        # Don't crash startup? Or do? Better to crash if critical.
        raise e


class SentimentRequest(BaseModel):
    text: str


class SentimentResponse(BaseModel):
    label: str
    score: float


@app.get("/health")
def health_check():
    if classifier is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/analyze", response_model=SentimentResponse)
def analyze_sentiment(request: SentimentRequest):
    if not classifier:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Analyze
    try:
        # Truncate if too long (FinBERT limit 512 tokens usually)
        # Pipeline handles truncation usually? Default might error.
        results = classifier(request.text, truncation=True, max_length=512)
        # results is [{'label': 'positive', 'score': 0.9}]
        result = results[0]
        return SentimentResponse(label=result["label"], score=result["score"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
