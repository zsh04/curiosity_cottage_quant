from typing import Optional, List
from sqlalchemy.orm import Session
from app.dal.models import (
    AgentStateSnapshot,
    AgentPerformanceMetrics,
    ModelPerformanceMetrics,
    TradeJournal,
)
from app.agent.state import AgentState
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StateService:
    """Manages persistence and retrieval of AgentState"""

    def __init__(self, db: Session):
        self.db = db

    def save_snapshot(self, state: AgentState) -> int:
        """Persist current state and return snapshot_id"""
        snapshot = AgentStateSnapshot(
            nav=state.get("nav", 0.0),
            cash=state.get("cash", 0.0),
            daily_pnl=state.get("daily_pnl", 0.0),
            max_drawdown=state.get("max_drawdown", 0.0),
            symbol=state.get("symbol", ""),
            price=state.get("price", 0.0),
            current_alpha=state.get("current_alpha", 0.0),
            regime=state.get("regime", "Unknown"),
            velocity=state.get("velocity", 0.0),
            acceleration=state.get("acceleration", 0.0),
            signal_side=state.get("signal_side", "FLAT"),
            signal_confidence=state.get("signal_confidence", 0.0),
            reasoning=state.get("reasoning", ""),
            approved_size=state.get("approved_size", 0.0),
            status=str(state.get("status", "SLEEPING")),
            messages=state.get("messages", []),
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)

        logger.info(f"✅ Saved snapshot {snapshot.id} at {snapshot.timestamp}")
        return snapshot.id

    def get_latest_snapshot(self) -> Optional[AgentStateSnapshot]:
        """Retrieve the most recent state"""
        return (
            self.db.query(AgentStateSnapshot)
            .order_by(AgentStateSnapshot.timestamp.desc())
            .first()
        )

    def get_recent_snapshots(self, limit: int = 10) -> List[AgentStateSnapshot]:
        """Get last N snapshots"""
        return (
            self.db.query(AgentStateSnapshot)
            .order_by(AgentStateSnapshot.timestamp.desc())
            .limit(limit)
            .all()
        )

    def save_agent_metrics(
        self,
        snapshot_id: int,
        agent_name: str,
        latency_ms: float,
        success: bool,
        output_data: dict,
        error: str = None,
    ):
        """Track individual agent performance"""
        metric = AgentPerformanceMetrics(
            snapshot_id=snapshot_id,
            agent_name=agent_name,
            latency_ms=latency_ms,
            success=success,
            error_message=error,
            output_data=output_data,
        )
        self.db.add(metric)
        self.db.commit()
        logger.debug(f"📊 Saved {agent_name} metrics: {latency_ms:.2f}ms")

    def save_model_metrics(
        self,
        snapshot_id: int,
        model_name: str,
        latency_ms: float,
        thought_process: str = None,
        prediction: dict = None,
        tokens_in: int = None,
        tokens_out: int = None,
        confidence: float = None,
    ):
        """Track model-level performance"""
        metric = ModelPerformanceMetrics(
            snapshot_id=snapshot_id,
            model_name=model_name,
            invocation_latency_ms=latency_ms,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            thought_process=thought_process,
            prediction=prediction,
            confidence=confidence,
        )
        self.db.add(metric)
        self.db.commit()
        logger.debug(f"🤖 Saved {model_name} metrics: {latency_ms:.2f}ms")

    def get_agent_metrics(self, limit: int = 30) -> dict:
        """Get recent agent performance grouped by agent"""
        metrics = (
            self.db.query(AgentPerformanceMetrics)
            .order_by(AgentPerformanceMetrics.timestamp.desc())
            .limit(limit)
            .all()
        )

        by_agent = {}
        for m in metrics:
            if m.agent_name not in by_agent:
                by_agent[m.agent_name] = []
            by_agent[m.agent_name].append(
                {
                    "timestamp": m.timestamp.isoformat(),
                    "latency_ms": m.latency_ms,
                    "success": m.success,
                    "output": m.output_data,
                    "error": m.error_message,
                }
            )

        return by_agent

    def get_model_metrics(self, limit: int = 50) -> dict:
        """Get recent model performance grouped by model"""
        metrics = (
            self.db.query(ModelPerformanceMetrics)
            .order_by(ModelPerformanceMetrics.timestamp.desc())
            .limit(limit)
            .all()
        )

        by_model = {}
        for m in metrics:
            if m.model_name not in by_model:
                by_model[m.model_name] = {
                    "avg_latency_ms": 0,
                    "invocations": [],
                    "last_thought": None,
                }

            by_model[m.model_name]["invocations"].append(
                {
                    "timestamp": m.timestamp.isoformat(),
                    "latency_ms": m.invocation_latency_ms,
                    "prediction": m.prediction,
                    "confidence": m.confidence,
                }
            )

            # Track latest reasoning
            if m.thought_process:
                by_model[m.model_name]["last_thought"] = m.thought_process

        # Calculate averages
        for model in by_model:
            invocations = by_model[model]["invocations"]
            if invocations:
                avg_latency = sum(i["latency_ms"] for i in invocations) / len(
                    invocations
                )
                by_model[model]["avg_latency_ms"] = avg_latency

        return by_model

    def create_trade_journal_entry(
        self,
        snapshot_id: int,
        symbol: str,
        side: str,
        requested_size: float,
        requested_price: float,
        requested_qty: float,
        alpha: float,
        regime: str,
        confidence: float,
    ) -> int:
        """Create a trade journal entry (Phase 1: simulation)"""
        entry = TradeJournal(
            snapshot_id=snapshot_id,
            symbol=symbol,
            side=side,
            requested_size=requested_size,
            requested_price=requested_price,
            requested_qty=requested_qty,
            filled_price=requested_price,  # Phase 1: assume perfect fill
            filled_qty=requested_qty,
            filled_size=requested_size,
            slippage_bps=0.0,  # Phase 1: no slippage
            alpha_at_execution=alpha,
            regime_at_execution=regime,
            signal_confidence=confidence,
            status="FILLED",  # Phase 1: instant fill
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        logger.info(
            f"📓 Trade Journal Entry {entry.id}: {side} {symbol} @ ${requested_price}"
        )
        return entry.id
