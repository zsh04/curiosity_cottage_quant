import asyncio
import logging
from app.services.brain_service import serve

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("🧠 Brain Server stopped.")
