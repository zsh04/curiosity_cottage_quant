from litestar import Controller, get
from dataclasses import dataclass


@dataclass
class SystemStatus:
    status: str
    active_agents: int
    version: str


@dataclass
class SystemMetrics:
    pnl_24h: float
    pnl_trend_pct: float
    system_load_pct: float
    open_positions: int


class SystemController(Controller):
    path = "/system"
    tags = ["system"]

    @get("/status")
    async def get_system_status(self) -> SystemStatus:
        """Get high-level system status."""
        return SystemStatus(status="Online", active_agents=8, version="2.0.0-alpha")

    @get("/metrics")
    async def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics (mock data for now)."""
        return SystemMetrics(
            pnl_24h=12450.00, pnl_trend_pct=2.4, system_load_pct=42.0, open_positions=14
        )
