from app.adapters.chronos import ChronosAdapter
import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class ForecastingService:
    """
    Forecasting Service: The 'Prophet' of the system.
    Wraps Chronos-2 to generate probabilistic future price paths.
    Interprets the forecast into actionable Trend and Confidence metrics.
    """

    def __init__(self):
        self.adapter = ChronosAdapter()

    def predict_trend(self, prices: List[float], horizon: int = 10) -> Dict[str, Any]:
        """
        Generate a trend prediction based on Chronos forecast.

        Args:
            prices: Chronological price history.
            horizon: Steps to forecast.

        Returns:
            {
                'trend': 'BULLISH' | 'BEARISH' | 'NEUTRAL',
                'confidence': float (0.0 - 1.0),
                'expected_price': float,
                'raw_forecast': dict
            }
        """
        if len(prices) < 10:
            return {
                "trend": "NEUTRAL",
                "confidence": 0.0,
                "expected_price": prices[-1] if prices else 0.0,
                "raw_forecast": {},
            }

        # Call Adapter
        forecast = self.adapter.predict(prices, horizon=horizon)

        if not forecast or not forecast.get("median"):
            return {
                "trend": "NEUTRAL",
                "confidence": 0.0,
                "expected_price": prices[-1],
                "raw_forecast": {},
            }

        # Interpret Forecast
        current_price = prices[-1]

        # We look at the end of the horizon
        future_median = forecast["median"][-1]
        future_low = forecast["low"][-1]
        future_high = forecast["high"][-1]

        # Trend Determination
        price_change = (future_median - current_price) / current_price

        trend = "NEUTRAL"
        if price_change > 0.005:  # > 0.5% up
            trend = "BULLISH"
        elif price_change < -0.005:  # < 0.5% down
            trend = "BEARISH"

        # Confidence Calculation
        # Narrower spread between low/high indicates higher confidence
        spread = (future_high - future_low) / current_price
        # Heuristic: Spread of 1% is high confidence, 5% is low.
        # Simple inversion: confidence = max(0, 1 - spread * 10)
        # This is a rough heuristic.
        confidence = max(0.0, min(1.0, 1.0 - (spread * 5)))

        return {
            "trend": trend,
            "confidence": round(confidence, 2),
            "expected_price": future_median,
            "forecast_horizon": horizon,
            "raw_forecast": forecast,
        }
