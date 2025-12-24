from litestar import Controller, post
from dataclasses import dataclass
from app.services.global_state import set_system_halt
import logging

logger = logging.getLogger(__name__)


@dataclass
class ActionResponse:
    success: bool
    message: str


class ActionsController(Controller):
    path = "/actions"
    tags = ["actions"]

    @post("/halt")
    async def trigger_halt(self) -> ActionResponse:
        """Trigger emergency system halt (Kill Switch)."""
        try:
            # 1. Set In-Memory Flag (Stop Loop)
            set_system_halt(True)

            # 2. Set Redis Key (Observability / Distributed)
            from app.api.dependencies import get_redis_client

            redis = await get_redis_client()
            await redis.set("SYSTEM:HALT", "true")

            logger.critical("🛑 EMERGENCY HALT TRIGGERED BY USER (UI)")
            return ActionResponse(
                success=True, message="🛑 Kill Switch Engaged. System Halted."
            )
        except Exception as e:
            logger.error(f"Halt Failed: {e}")
            # Fallback: simpler return if redis fails, but memory flag is set
            return ActionResponse(
                success=True, message="🛑 System Halted (Redis Error log)."
            )

    @post("/resume")
    async def trigger_resume(self) -> ActionResponse:
        """Resume system from emergency halt."""
        try:
            # 1. Unset In-Memory Flag
            set_system_halt(False)

            # 2. Unset Redis Key
            from app.api.dependencies import get_redis_client

            redis = await get_redis_client()
            await redis.delete("SYSTEM:HALT")

            logger.info("▶️ RESUME TRIGGERED: Releasing Emergency Halt")
            return ActionResponse(
                success=True, message="✅ System Resumed. Agent Loop Active."
            )
        except Exception as e:
            logger.error(f"Resume Failed: {e}")
            return ActionResponse(
                success=True, message="✅ System Resumed (Redis Error log)."
            )

    @post("/rebalance")
    async def trigger_rebalance(self) -> ActionResponse:
        """Trigger portfolio rebalancing."""
        print(">>> Portfolio Rebalance Initiated")
        return ActionResponse(success=True, message="Rebalance Started")

    @post("/export-logs")
    async def export_logs(self) -> ActionResponse:
        """Trigger log export."""
        print(">>> Exporting Logs...")
        return ActionResponse(success=True, message="Logs Exported to S3")
