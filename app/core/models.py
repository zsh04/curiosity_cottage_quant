from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ForceVector(BaseModel):
    """
    The 5 Pillars of Physics Output Vector.
    """

    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime = Field(..., description="Tick Timestamp")
    symbol: str = Field(..., description="Ticker Symbol")

    # The 5 Pillars
    mass: float = Field(..., description="Volume * CLV")
    momentum: float = Field(..., description="Mass * Velocity")
    friction: float = Field(..., description="TradeCount / Volume")
    entropy: float = Field(..., description="Shannon Entropy of Returns")
    nash_dist: float = Field(..., description="Z-Score Distance from Mode")

    # Extra
    alpha_coefficient: float = Field(default=2.0, description="Tail Index (Alpha)")


from enum import Enum
from typing import Dict, Any


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradeSignal(BaseModel):
    """
    Soros Reflexivity Output.
    """

    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime = Field(..., description="Signal Generation Time")
    symbol: str = Field(..., description="Ticker Symbol")
    side: Side = Field(..., description="Direction: BUY, SELL, or HOLD")
    strength: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence/Aggression (0.0 - 1.0)"
    )
    meta: Dict[str, Any] = Field(default_factory=dict, description="Reasoning Logs")
