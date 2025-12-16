from litestar import Controller, get
from litestar.di import Provide
from dataclasses import dataclass
from typing import Dict, Any
from app.services.state_service import StateService
from app.dal.database import get_db


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
    dependencies = {"state_service": Provide(lambda: StateService(next(get_db())))}

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

    @get("/state/current")
    async def get_current_state(self, state_service: StateService) -> Dict[str, Any]:
        """Return latest AgentState for Terminal UI"""
        snapshot = state_service.get_latest_snapshot()

        if not snapshot:
            return {"error": "No state available", "status": "offline"}

        return {
            "timestamp": snapshot.timestamp.isoformat(),
            "status": snapshot.status,
            "market": {
                "symbol": snapshot.symbol,
                "price": snapshot.price,
                "alpha": snapshot.current_alpha,
                "regime": snapshot.regime,
                "velocity": snapshot.velocity,
                "acceleration": snapshot.acceleration,
            },
            "portfolio": {
                "nav": snapshot.nav,
                "cash": snapshot.cash,
                "daily_pnl": snapshot.daily_pnl,
                "max_drawdown": snapshot.max_drawdown,
            },
            "signal": {
                "side": snapshot.signal_side,
                "confidence": snapshot.signal_confidence,
                "reasoning": snapshot.reasoning,
            },
            "governance": {"approved_size": snapshot.approved_size},
            "logs": snapshot.messages[-10:] if snapshot.messages else [],
        }

    @get("/state/history")
    async def get_state_history(
        self, state_service: StateService, limit: int = 10
    ) -> Dict[str, Any]:
        """Return recent state snapshots"""
        snapshots = state_service.get_recent_snapshots(limit)

        return {
            "count": len(snapshots),
            "snapshots": [
                {
                    "id": s.id,
                    "timestamp": s.timestamp.isoformat(),
                    "alpha": s.current_alpha,
                    "regime": s.regime,
                    "signal_side": s.signal_side,
                    "approved_size": s.approved_size,
                    "status": s.status,
                }
                for s in snapshots
            ],
        }

    @get("/metrics/agents")
    async def get_agent_metrics(self, state_service: StateService) -> Dict[str, Any]:
        """Return latest performance metrics for all agents"""
        return state_service.get_agent_metrics(limit=30)

    @get("/metrics/models")
    async def get_model_metrics(self, state_service: StateService) -> Dict[str, Any]:
        """Return latest model performance (FinBERT, Gemma2, Chronos)"""
        return state_service.get_model_metrics(limit=50)

    @get("/status/physics")
    async def get_physics_status(self, state_service: StateService) -> Dict[str, Any]:
        """
        Return latest physics metrics for dashboard.

        Returns:
            alpha: Tail risk exponent (default 3.0)
            velocity: Kinematic velocity
            acceleration: Kinematic acceleration
            regime: Market regime (Gaussian/Lévy Stable/Critical)
            timestamp: When metrics were captured
        """
        snapshot = state_service.get_latest_snapshot()

        if not snapshot:
            # Return safe defaults if no history
            return {
                "alpha": 3.0,
                "velocity": 0.0,
                "acceleration": 0.0,
                "regime": "Unknown",
                "timestamp": None,
            }

        return {
            "alpha": snapshot.current_alpha or 3.0,
            "velocity": snapshot.velocity or 0.0,
            "acceleration": snapshot.acceleration or 0.0,
            "regime": snapshot.regime or "Unknown",
            "timestamp": snapshot.timestamp.isoformat() if snapshot.timestamp else None,
        }
