import sys
import os
import logging
from datetime import datetime

# Ensure app is in path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.services.memory import MemoryService


def test_memory_service():
    print("🧠 Testing MemoryService (LanceDB)...")

    try:
        memory = MemoryService(db_path="data/lancedb_test")

        if not memory.embedding_model:
            print("⚠️ Embedding model not found. Skipping test.")
            return

        # 1. Create Dummy State
        symbol = "BTC-USD"
        physics = {
            "regime": "Gaussian",
            "alpha": 3.5,
            "velocity": 100.0,
            "acceleration": 5.0,
        }
        sentiment = {"label": "positive", "score": 0.95}

        print(f"🔹 Saving State for {symbol}...")
        memory.save_regime(symbol, physics, sentiment)

        # 2. Retrieve Similar
        print(f"🔹 Retrieving Similar States...")
        # Create a slightly different state to query
        query_physics = {
            "regime": "Gaussian",
            "alpha": 3.4,  # Close to 3.5
            "velocity": 90.0,
            "acceleration": 4.0,
        }

        results = memory.retrieve_similar(symbol, query_physics, sentiment, k=1)

        if results:
            print(f"✅ Retrieved {len(results)} result(s).")
            top_match = results[0]
            print(f"   Shape: {top_match.keys()}")
            print(f"   Distance: {top_match['distance']:.4f}")
            print(f"   Metadata: {top_match['metadata']}")
        else:
            print("❌ No results retrieved.")

    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_memory_service()
