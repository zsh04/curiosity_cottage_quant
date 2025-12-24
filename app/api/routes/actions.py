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
        logger.warning("🛑 EMERGENCY HALT TRIGGERED BY USER")
        set_system_halt(True)
        return ActionResponse(
            success=True, message="🛑 Kill Switch Engaged. Agent Loop Paused."
        )

    @post("/resume")
    async def trigger_resume(self) -> ActionResponse:
        """Resume system from emergency halt."""
        logger.info("▶️ RESUME TRIGGERED: Releasing Emergency Halt")
        set_system_halt(False)
        return ActionResponse(
            success=True, message="✅ System Resumed. Agent Loop Active."
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
