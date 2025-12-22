from litestar import Controller, post
from app.api.dependencies import get_redis_client
from redis.asyncio import Redis
import logging
import orjson

logger = logging.getLogger("SystemAPI")


class SystemController(Controller):
    path = "/system"

    @post("/halt")
    async def halt_system(self) -> dict:
        """
        THE KILL SWITCH.
        Halts all trading logic immediately.
        """
        try:
            redis = await get_redis_client()
            await redis.set("SYSTEM:HALT", "true")

            # Broadcast Event
            msg = {
                "event": "SYSTEM_HALT",
                "data": {"status": "HALTED", "reason": "Manual Kill Switch"},
            }
            await redis.publish("system_events", orjson.dumps(msg).decode())

            logger.critical("🚨 KILL SWITCH ACTIVATED VIA API 🚨")
            return {"status": "HALTED", "message": "System Halt sequence initiated."}
        except Exception as e:
            logger.error(f"Kill Switch Failed: {e}")
            return {"status": "ERROR", "message": str(e)}

    @post("/resume")
    async def resume_system(self) -> dict:
        """
        Resume Trading logic.
        """
        try:
            redis = await get_redis_client()
            await redis.delete("SYSTEM:HALT")

            msg = {
                "event": "SYSTEM_RESUME",
                "data": {"status": "ACTIVE", "reason": "Manual Resume"},
            }
            await redis.publish("system_events", orjson.dumps(msg).decode())

            logger.info("✅ System Resumed via API.")
            return {"status": "ACTIVE", "message": "System resumed."}
        except Exception as e:
            logger.error(f"Resume Failed: {e}")
            return {"status": "ERROR", "message": str(e)}
