"""Vector data types for agent outputs.

Defines PhysicsVector (Feynman), ReflexivityVector (Soros), and OODAVector (Boyd).
"""

from pydantic import BaseModel, Field


class PhysicsVector(BaseModel):
    """
    Feynman's Output: The Kinematic State.
    """

    mass: float = Field(..., description="Volume or Liquidity Mass")
    momentum: float = Field(..., description="Price Velocity (p)")
    entropy: float = Field(..., description="Market Entropy (s)")
    jerk: float = Field(..., description="3rd Derivative of Price (j)")
    nash_dist: float = Field(default=0.0, description="Distance from Mode (N)")
    alpha_coefficient: float = Field(default=2.5, description="Tail Risk Alpha")
    price: float = Field(default=0.0, description="Current Price")


class ReflexivityVector(BaseModel):
    """
    Soros's Output: The Mirror Test.
    """

    sentiment_delta: float = Field(..., description="Change in Sentiment")
    reflexivity_index: float = Field(..., description="Correlation(MyVol, PriceChange)")


class OODAVector(BaseModel):
    """
    Boyd's Output: The Decision.
    """

    urgency_score: float = Field(
        ..., ge=0.0, le=1.0, description="Urgency (0.0=Wait, 1.0=Act Now)"
    )
