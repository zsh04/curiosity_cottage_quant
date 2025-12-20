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
    price: float = Field(..., description="Current Price for Sizing")
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
    price: float = Field(..., description="Reference Price for Execution")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Reasoning Logs")


class OrderPacket(BaseModel):
    """
    Execution Gate Output.
    """

    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime = Field(..., description="Order Generation Time")
    signal_id: str = Field(..., description="Origin Signal UUID")
    symbol: str = Field(..., description="Ticker Symbol")
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., description="Sized Quantity")
    order_type: str = Field(default="MARKET", description="Order Type")
    risk_check_passed: bool = Field(..., description="Did it pass the Ruin checks?")


class ForecastPacket(BaseModel):
    """
    Chronos Probabilistic Output.
    """

    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime = Field(..., description="Forecast Generation Time")
    symbol: str = Field(..., description="Ticker Symbol")
    p10: float = Field(..., description="10th Percentile (Lower Bound)")
    p50: float = Field(..., description="50th Percentile (Median)")
    p90: float = Field(..., description="90th Percentile (Upper Bound)")
    horizon: int = Field(..., description="Forecast Steps Ahead")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Spread Confidence (Derived)"
    )
