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
    # **SYNODIC_MONTH = 29.53058867** (Lunar Cycle Length):
    # - Theory: Astronomical precision (synodic month)
    # - Definition: Time between identical moon phases
    # - Source: NASA JPL (Jet Propulsion Laboratory)
    # - Precision: 8 decimal places (accurate to ~1 second)
    # - Why not 29.5: True value is 29.530588 days
    # - Historical: Used in calendars for millennia
    # - Reference: Meeus (1998) "Astronomical Algorithms"
    SYNODIC_MONTH = 29.53058867

    # **REF_NEW_MOON** (Reference Point for Phase Calculation):
    # - Date: Jan 6, 2000 18:14 UTC
    # - Source: NASA confirmed new moon
    # - Purpose: Anchor point for phase calculations
    # - All phases calculated relative to this timestamp
    # - Accuracy: Critical for phase determination
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

            # **Moon Phase Trading Thresholds** (Astrological Constants):
            #
            # 1. **New Moon: 0.98-1.0 OR 0.0-0.02** (Buy Signal):
            #    - Rationale: Moon reborn = Market reborn (renewal energy)
            #    - Threshold: 0.98-1.0 (wraparound at cycle end)
            #    - Plus: 0.0-0.02 (beginning of new cycle)
            #    - Total window: ~4% of cycle (1.2 days)
            #    - Alternative: 0.96-1.0/0.0-0.04 (wider, 2.4 days)
            #    - Historical: Many cultures mark new moon as auspicious
            #    - Empirical note: No statistical edge proven in finance
            #
            # 2. **Full Moon: 0.48-0.52** (Sell Signal):
            #    - Rationale: Peak lunar energy = Market peak (sell high)
            #    - Threshold: ±2% around 0.5 (full moon)
            #    - Total window: 4% of cycle (1.2 days)
            #    - Alternative: 0.45-0.55 (wider, 3 days)
            #    - Folklore: "Lunacy" etymology (luna = moon)
            #    - Empirical: Dichev & Janes (2003) found weak effect
            #
            # **Academic Note**: This strategy is experimental/educational.
            # Multiple studies show no consistent lunar effect in markets.
            # Reference: Yuan et al. (2006) "Lunar Phases and Stock Returns"

            signal = 0.0
            # New Moon (Buy): 0.98 <= phase <= 1.0 OR 0.0 <= phase <= 0.02
            if phase >= 0.98 or phase <= 0.02:
                signal = 1.0
            # Full Moon (Sell): 0.48 <= phase <= 0.52
            elif 0.48 <= phase <= 0.52:
                signal = -1.0

            span.set_attribute("moon.signal", signal)

            return signal
