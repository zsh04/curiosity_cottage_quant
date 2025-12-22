import asyncio
import os
import sys
import shutil

# Add project root to path
sys.path.append(os.getcwd())

from app.services.memory import MemoryService
from app.core.models import MarketStateEmbedding


async def verify_lancedb():
    print("🧠 Verifying LanceDB Pattern Memory...")

    # Clean test path
    test_db = "data/lancedb_test"
    if os.path.exists(test_db):
        shutil.rmtree(test_db)

    svc = MemoryService(db_path=test_db)

    if svc.db is None:
        print("❌ Failed to init LanceDB")
        return

    # Mock Data
    symbol = "BTC"
    physics = {"regime": "Leptokurtic", "alpha": 1.5, "velocity": 0.05}
    sentiment = {"label": "Bullish", "score": 0.9}

    # 1. Save
    print("1. Saving Regime...")
    svc.save_regime(symbol, physics, sentiment)

    # 2. Retrieve
    print("2. Retrieving Similar...")
    # Should find itself
    results = svc.retrieve_similar(symbol, physics, sentiment, k=1)

    if not results:
        print("❌ Retrieval failed (or model download failed)")
    else:
        print(f"✅ Retrieved {len(results)} matches.")
        print(f"   Top Match Distance: {results[0]['distance']:.4f}")
        print(f"   MetaData: {results[0]['metadata']}")

    # Cleanup
    if os.path.exists(test_db):
        shutil.rmtree(test_db)
        print("🧹 Cleanup done.")


if __name__ == "__main__":
    asyncio.run(verify_lancedb())
