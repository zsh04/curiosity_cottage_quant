from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Text,
    JSON,
    Boolean,
    Index,
)

from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class AgentStateSnapshot(Base):
    """Immutable snapshot of AgentState after each graph execution"""

    __tablename__ = "agent_state_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Portfolio
    nav = Column(Float)
    cash = Column(Float)
    daily_pnl = Column(Float)
    max_drawdown = Column(Float)

    # Market
    symbol = Column(String(10))
    price = Column(Float)

    # Physics
    current_alpha = Column(Float, index=True)  # KEY METRIC
    regime = Column(String(20))
    velocity = Column(Float)
    acceleration = Column(Float)

    # Signal
    signal_side = Column(String(10))
    signal_confidence = Column(Float)
    reasoning = Column(Text)

    # Governance
    approved_size = Column(Float)
    status = Column(String(30))

    # Audit Trail
    messages = Column(JSON)  # Full log array


class AgentPerformanceMetrics(Base):
    """Per-agent execution metrics"""

    __tablename__ = "agent_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    snapshot_id = Column(Integer)  # FK to AgentStateSnapshot

    agent_name = Column(String(50), index=True)  # analyst, risk, execution
    latency_ms = Column(Float)
    success = Column(Boolean)
    error_message = Column(Text, nullable=True)

    # Agent-specific outputs
    output_data = Column(JSON)  # Flexible for each agent's unique data


class ModelPerformanceMetrics(Base):
    """Model-level performance (FinBERT, Gemma2, Chronos)"""

    __tablename__ = "model_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    snapshot_id = Column(Integer)

    model_name = Column(String(50), index=True)  # finbert, gemma2, chronos
    invocation_latency_ms = Column(Float)

    # LLM-specific
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    thought_process = Column(Text, nullable=True)  # Raw LLM response

    # Model output
    prediction = Column(JSON)
    confidence = Column(Float, nullable=True)


class TradeJournal(Base):
    """Trade execution journal - tracks filled vs expected outcomes"""

    __tablename__ = "trade_journal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    snapshot_id = Column(Integer)  # FK to snapshot when trade was executed

    # Trade Details
    symbol = Column(String(10), index=True)
    side = Column(String(10))  # BUY, SELL

    # Requested vs Actual
    requested_size = Column(Float)  # approved_size from Risk
    requested_price = Column(Float)  # price at signal time
    requested_qty = Column(Float)  # calculated quantity

    filled_price = Column(Float, nullable=True)  # actual fill price
    filled_qty = Column(Float, nullable=True)  # actual filled quantity
    filled_size = Column(Float, nullable=True)  # actual notional filled

    # Execution Quality
    slippage_bps = Column(
        Float, nullable=True
    )  # (filled - requested) / requested * 10000
    execution_latency_ms = Column(Float, nullable=True)

    # Context
    alpha_at_execution = Column(Float)  # tail risk at time of trade
    regime_at_execution = Column(String(20))  # regime at time of trade
    signal_confidence = Column(Float)  # analyst confidence

    # Status
    status = Column(String(20))  # PENDING, FILLED, PARTIAL, REJECTED, CANCELLED
    rejection_reason = Column(Text, nullable=True)


# ============================================
# TIME-SERIES MODELS (TimescaleDB Hypertables)
# ============================================
