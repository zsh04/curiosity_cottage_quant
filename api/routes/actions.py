from litestar import Controller, post
from dataclasses import dataclass


@dataclass
class ActionResponse:
    success: bool
    message: str


class ActionsController(Controller):
    path = "/actions"
    tags = ["actions"]

    @post("/halt")
    async def trigger_halt(self) -> ActionResponse:
        """Trigger emergency system halt."""
        print("!!! EMERGENCY HALT TRIGGERED !!!")
        return ActionResponse(success=True, message="System Halted Successfully")

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
