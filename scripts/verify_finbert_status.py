import logging
# os and sys were removed as they were unused

# Configure logging to capture the adapter's output
logging.basicConfig(level=logging.INFO)

# Run verification
try:
    from app.adapters.sentiment import SentimentAdapter

    print("⏳ Initializing SentimentAdapter...")
    adapter = SentimentAdapter()

    test_text = "The market is bullish and profits are soaring."
    print(f"🧪 Analyzing text: '{test_text}'")

    result = adapter.analyze(test_text)
    print(f"✅ Result: {result}")

    if result["label"] in ["positive", "negative", "neutral"]:
        print("🎉 SUCCESS: FinBERT is connected and running (Fallback Mode expected).")
    else:
        print("❌ FAILURE: Invalid output format.")
        exit(1)

except ImportError as e:
    print(f"❌ ImportError: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Runtime Exception: {e}")
    exit(1)
