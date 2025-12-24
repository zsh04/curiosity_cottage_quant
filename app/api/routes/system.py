from litestar import Controller, get, post
from litestar.di import Provide
from dataclasses import dataclass
from typing import Dict, Any
from sqlalchemy.orm import Session
import orjson
import logging
import os
from redis.asyncio import Redis


from app.services.state_service import StateService
from app.services.global_state import set_system_halt
from app.api.dependencies import get_redis_client
from app.dal.database import get_db

logger = logging.getLogger("SystemAPI")


async def provide_state_service(db_session: Session) -> StateService:
    return StateService(db_session)


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
    dependencies = {
        "state_service": Provide(provide_state_service),
        "db_session": Provide(get_db),
    }

    # ========================================================================
    # KILL SWITCH
    # ========================================================================

    @post("/halt")
    async def halt_system(self) -> dict:
        """
        THE KILL SWITCH.
        Halts all trading logic immediately.
        """
        try:
            # 1. Set In-Memory Flag (Immediate Effect on Local Loop)
            set_system_halt(True)

            redis = await get_redis_client()
            await redis.set("SYSTEM:HALT", "true")

            # Broadcast Event
            msg = {
                "event": "SYSTEM_HALT",
                "data": {"status": "HALTED", "reason": "Manual Kill Switch"},
            }
            await redis.publish("system_events", orjson.dumps(msg).decode())

            logger.critical("🚨 KILL SWITCH ACTIVATED VIA API (System Controller) 🚨")
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
            # 1. Unset In-Memory Flag
            set_system_halt(False)

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

    # ========================================================================
    # METRICS & OBSERVABILITY
    # ========================================================================

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
