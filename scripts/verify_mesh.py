import asyncio
import logging
import grpc
import redis
import sys
import os
import orjson
import torch

# Add project root
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.generated import brain_pb2 as pb2
from app.generated import brain_pb2_grpc as pb2_grpc
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | VERIFY | %(message)s")
logger = logging.getLogger("verify_mesh")


async def test_brain_connection():
    logger.info("🧠 Testing Brain Service Connection (gRPC)...")
    try:
        channel = grpc.aio.insecure_channel("localhost:50051")
        stub = pb2_grpc.BrainStub(channel)

        # Test Forecast
        prices = [100.0 + i for i in range(64)]
        req = pb2.ForecastRequest(ticker="TEST_MESH", prices=prices, horizon=12)

        logger.info("   Sending Forecast Request...")
        resp = await stub.Forecast(req)

        logger.info(f"   ✅ Brain Response Received!")
        logger.info(f"      Signal: {resp.signal}")
        logger.info(f"      Confidence: {resp.confidence:.2f}")
        logger.info(f"      P50: {resp.p50:.2f}")
        logger.info(f"      Full Quantiles (Count): {len(resp.full_quantiles)}")

        return True
    except grpc.RpcError as e:
        logger.error(f"   ❌ Brain Service Failed: {e.code()} - {e.details()}")
        logger.warning(
            "   (Make sure `python app/services/brain_service.py` is running!)"
        )
        return False
    except Exception as e:
        logger.error(f"   ❌ Unexpected Error: {e}")
        return False


async def test_nervous_system():
    logger.info("⚡ Testing Nervous System (Redis)...")
    try:
        redis_url = getattr(
            settings, "REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379")
        )
        r = redis.Redis.from_url(redis_url, decode_responses=True)
        if r.ping():
            logger.info("   ✅ Redis Alive.")

        # Check Channels
        # We can't easily check pubs without a listener, but we can check if Keys exist
        # if the system was running.
        # For now, just Write/Read verify.
        r.set("mesh:verify", "alive")
        val = r.get("mesh:verify")
        if val == "alive":
            logger.info("   ✅ R/W Verified.")

        return True
    except Exception as e:
        logger.error(f"   ❌ Redis Failed: {e}")
        return False


async def main():
    logger.info("=== STARTING MESH VERIFICATION ===")

    redis_ok = await test_nervous_system()
    brain_ok = await test_brain_connection()

    if redis_ok and brain_ok:
        logger.info("=== 🟢 MESH STATUS: OPERATIONAL ===")
        sys.exit(0)
    else:
        logger.info("=== 🔴 MESH STATUS: PARTIAL / OFFLINE ===")
        # We exit 0 to allow the script to finish, but log clearly.
        # Actually fail if CI.
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
