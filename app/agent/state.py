from typing import TypedDict, List
from enum import Enum


class TradingStatus(str, Enum):
    ACTIVE = "ACTIVE"
    HALTED_PHYSICS = "HALTED_PHYSICS"
    HALTED_DRAWDOWN = "HALTED_DRAWDOWN"
    SLEEPING = "SLEEPING"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    FLAT = "FLAT"


class AgentState(TypedDict):
    """
    State for the Curiosity Cottage V2 trading engine, supporting the
    Risk-Execution Handshake.
    """

    # --- Portfolio ---
    nav: float
    cash: float
    daily_pnl: float
    max_drawdown: float

    # --- Market ---
    symbol: str
    price: float
    historic_returns: List[float]

    # --- Physics ---
    # --- Physics ---
    current_alpha: float
    regime: str
    hurst: float
    strategy_mode: str
    hurst: float
    strategy_mode: str
    chronos_forecast: dict

    # --- Meta-Reasoning ---
    performance_metrics: dict  # Keys: trend_win_rate, reversion_win_rate

    # --- Signal (The Analyst's Input) ---
    signal_side: str
    signal_confidence: float
    reasoning: str

    # --- Governance (The Risk Output) ---
    approved_size: float
    risk_multiplier: float

    # --- Audit ---
    status: TradingStatus
    messages: List[str]

    # --- Quantum Batch (New) ---
    candidates: List[dict]
