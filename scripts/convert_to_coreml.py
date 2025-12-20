# scripts/convert_to_coreml.py
import torch
import numpy as np
import coremltools as ct
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import os

MODEL_NAME = "ProsusAI/finbert"
OUTPUT_PATH = "metal/models/finbert.mlpackage"


def convert():
    print(f"Loading {MODEL_NAME}...")
    # Load model and tokenizer
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, torchscript=True
    ).eval()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    # Create dummy input for tracing (Batch size 1, Sequence length 128)
    dummy_input_ids = torch.randint(0, tokenizer.vocab_size, (1, 128))
    dummy_attention_mask = torch.ones((1, 128), dtype=torch.int64)

    # Trace the model
    print("Tracing model with torch.jit.trace...")
    traced_model = torch.jit.trace(model, (dummy_input_ids, dummy_attention_mask))

    # Define CoreML inputs
    inputs = [
        ct.TensorType(name="input_ids", shape=(1, 128), dtype=np.int32),
        ct.TensorType(name="attention_mask", shape=(1, 128), dtype=np.int32),
    ]

    # Convert to CoreML
    print("Converting to CoreML (ANE Optimized)...")
    mlmodel = ct.convert(
        traced_model,
        inputs=inputs,
        compute_units=ct.ComputeUnit.ALL,
        classifier_config=ct.ClassifierConfig(["positive", "negative", "neutral"]),
        minimum_deployment_target=ct.target.iOS16,  # Ensures support for float16/ANE
    )

    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # Save
    mlmodel.save(OUTPUT_PATH)
    print(f"Saved optimized model to {OUTPUT_PATH}")


if __name__ == "__main__":
    convert()
