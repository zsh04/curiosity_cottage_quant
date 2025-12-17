import pandas as pd
import numpy as np
from datetime import datetime
from app.strategies.base import BaseStrategy


class MoonPhaseStrategy(BaseStrategy):
    """
    Moon Phase Strategy (MoonPhase_V1).

    Trading logic based on lunar cycles:
    - New Moon: Buy
    - Full Moon: Sell
    """

    # Astronomical Constants
    SYNODIC_MONTH = 29.53058867
    REF_NEW_MOON = datetime(2000, 1, 6, 18, 14)  # Jan 6, 2000 18:14 UTC

    @property
    def name(self) -> str:
        return "MoonPhase_V1"

    def calculate_phase(self, timestamp: pd.Timestamp) -> float:
        """
        Calculates the moon phase (0.0 to 1.0) for a given timestamp.
        0.0 = New Moon, 0.5 = Full Moon, 1.0 = New Moon.
        """
        delta = timestamp - self.REF_NEW_MOON
        days_passed = delta.total_seconds() / 86400.0
        phase = (days_passed % self.SYNODIC_MONTH) / self.SYNODIC_MONTH
        return phase

    def calculate_signal(self, market_data: pd.DataFrame) -> float:
        """
        Generates signal based on the phase of the moon for the *latest* data point.
        """
        with self.tracer.start_as_current_span("calculate_signal") as span:
            if market_data.empty:
                return 0.0

            # Use the latest timestamp from the index
            current_time = market_data.index[-1]
            phase = self.calculate_phase(current_time)

            span.set_attribute("moon.phase", phase)
            span.set_attribute("moon.time", str(current_time))

            signal = 0.0
            # New Moon (Buy): 0.98 <= phase <= 1.0 OR 0.0 <= phase <= 0.02
            if phase >= 0.98 or phase <= 0.02:
                signal = 1.0
            # Full Moon (Sell): 0.48 <= phase <= 0.52
            elif 0.48 <= phase <= 0.52:
                signal = -1.0

            span.set_attribute("moon.signal", signal)

            return signal
