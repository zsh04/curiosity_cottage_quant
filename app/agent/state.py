"""
Shared State Schema (TypedDict).
"""

from typing import TypedDict, Optional, List
from enum import Enum


class TradingStatus(Enum):
    ACTIVE = "active"
    HALTED_PHYSICS = "halted_physics"
    HALTED_DRAWDOWN = "halted_drawdown"
    SLEEPING = "sleeping"


class AgentState(TypedDict):
    # --- Portfolio State ---
    nav: float  # Net Asset Value
    cash: float  # Available Cash
    daily_pnl: float  # Check for 2% stop
    max_drawdown: float  # Check for 20% ruin

    # --- Market State ---
    current_alpha: float  # Hill Estimator Value
    regime: str  # Gaussian, Levy, Critical

    # --- Trading Signals ---
    # We can add more specific signal fields later

    # --- Governance ---
    status: TradingStatus
    messages: List[str]  # Audit log of decisions
