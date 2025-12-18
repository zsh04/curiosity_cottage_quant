import logging
import sys
import os

# Ensure app is in path
sys.path.append(os.getcwd())

from app.services.memory import MemoryService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyMemory")


def verify():
    logger.info("Initializing MemoryService...")
    memory = MemoryService()

    if not memory.embedding_model:
        logger.error("Embedding model failed to load. Install sentence-transformers.")
        return

    symbol = "TEST/USD"
    physics = {"alpha": 1.5, "velocity": 0.01, "regime": "Lévy Stable"}
    sentiment = {"label": "Positive", "score": 0.8}

    logger.info(f"Saving regime for {symbol}...")
    try:
        memory.save_regime(symbol, physics, sentiment)
        logger.info("✅ Save successful.")
    except Exception as e:
        logger.error(f"❌ Save failed: {e}")
        return

    logger.info("Retrieving similar...")
    try:
        results = memory.retrieve_similar(symbol, physics, sentiment, k=1)
        if results:
            logger.info(
                f"✅ Retrieved {len(results)} results. Top distance: {results[0]['distance']}"
            )
        else:
            logger.warning("⚠️ Retrieved 0 results.")
    except Exception as e:
        logger.error(f"❌ Retrieve failed: {e}")


if __name__ == "__main__":
    verify()
