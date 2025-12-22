from typing import TypedDict, List
from enum import Enum


class TradingStatus(str, Enum):
    ACTIVE = "ACTIVE"
    HALTED_PHYSICS = "HALTED_PHYSICS"
    HALTED_DRAWDOWN = "HALTED_DRAWDOWN"
    HALTED_SYSTEM = "HALTED_SYSTEM"
    SLEEPING = "SLEEPING"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    FLAT = "FLAT"


class CognitiveState(TypedDict):
    """
    Self-regulating psychological state of the agent.

    Attributes:
        consecutive_losses: Running count of bad trades.
        anxiety_score: Float 0.0-1.0. Increases with losses/volatility.
                        > 0.7 triggers defensive sizing.
        regret_matrix: List of missed opportunities (Symbol, Expected Return).
    """

    consecutive_losses: int
    anxiety_score: float
    regret_matrix: List[dict]


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
    analysis_reports: List[dict]  # Required for Risk Node
    watchlist: List[dict]  # Required for Analyst Node

    # --- Physics State ---
    velocity: float  # Required for Telemetry
    acceleration: float  # Required for Telemetry
    history: List[float]  # Required for Charts

    # --- Portfolio Awareness (Phase 13) ---
    # --- Portfolio Awareness (Phase 13) ---
    current_positions: List[dict]

    # --- Phase 32: Meta-Cognition ---
    cognitive_state: CognitiveState
