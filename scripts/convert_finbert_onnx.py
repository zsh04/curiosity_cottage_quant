import os
import torch
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer, AutoModelForSequenceClassification


def convert_and_verify():
    model_id = "ProsusAI/finbert"
    output_dir = "models/finbert_onnx"
    onnx_model_path = os.path.join(output_dir, "model.onnx")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"⬇️ Downloading {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(model_id)
    model.eval()

    # Create dummy input for export trace
    dummy_text = "Markets are volatile"
    inputs = tokenizer(dummy_text, return_tensors="pt")

    # Check if token_type_ids is in inputs (BERT usually keeps it)
    input_names = ["input_ids", "attention_mask"]
    dynamic_axes = {
        "input_ids": {0: "batch_size", 1: "sequence_length"},
        "attention_mask": {0: "batch_size", 1: "sequence_length"},
        "logits": {0: "batch_size"},
    }
    model_args = (inputs["input_ids"], inputs["attention_mask"])

    if "token_type_ids" in inputs:
        input_names.append("token_type_ids")
        dynamic_axes["token_type_ids"] = {0: "batch_size", 1: "sequence_length"}
        model_args = (
            inputs["input_ids"],
            inputs["attention_mask"],
            inputs["token_type_ids"],
        )

    # Export
    print(f"🔄 Converting to ONNX (opset=14)...")
    torch.onnx.export(
        model,
        model_args,
        onnx_model_path,
        opset_version=14,
        input_names=input_names,
        output_names=["logits"],
        dynamic_axes=dynamic_axes,
        do_constant_folding=True,
    )

    # Save tokenizer for reuse with ONNX model
    tokenizer.save_pretrained(output_dir)
    print(f"✅ Saved ONNX model and tokenizer to {output_dir}")

    # Verify
    verify_onnx(onnx_model_path, tokenizer, model.config.id2label)


def verify_onnx(model_path, tokenizer, id2label):
    print("\n🧪 Verifying ONNX Model...")
    session = ort.InferenceSession(model_path)

    text = "Markets are volatile and uncertain."
    inputs = tokenizer(text, return_tensors="np")

    ort_inputs = {
        k: v for k, v in inputs.items() if k in [x.name for x in session.get_inputs()]
    }

    # Run Inference
    logits = session.run(None, ort_inputs)[0]

    # Softmax
    def softmax(x):
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum(axis=0)

    probs = softmax(logits[0])

    print(f"Input: '{text}'")
    for i, prob in enumerate(probs):
        label = id2label.get(i, f"Label {i}")
        print(f"  - {label}: {prob:.4f}")

    print("✅ ONNX Verification Successful!")


if __name__ == "__main__":
    convert_and_verify()
