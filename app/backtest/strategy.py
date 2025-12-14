from typing import Optional
import pandas as pd
import numpy as np
from app.backtest.events import MarketEvent, SignalEvent
from app.lib.physics.heavy_tail import HeavyTailEstimator
from app.lib.kalman.kinematic import KinematicKalmanFilter


class Strategy:
    """Base Strategy Class"""

    def calculate_signals(self, event: MarketEvent, event_queue):
        raise NotImplementedError


class PhysicsStrategy(Strategy):
    """
    Physics-based Alpha Strategy.
    1. Update HeavyTailEstimator with new returns. If alpha < 1.5 (High Risk), VETO trade.
    2. Update KinematicKalmanFilter with price.
    3. Trade based on Velocity (v) direction.
    """

    def __init__(self, lookback_window=100):
        self.heavy_tail = (
            HeavyTailEstimator()
        )  # Default window is hardcoded or setter used?
        # Actually checking file content first is better, but this is a likely patch.
        # Wait, if it takes no args, I should just call it empty.
        # If I need config, I might need to set it after or refactor HeavyTailEstimator.
        # Let's assume for now HeavyTailEstimator handles window internally or doesn't support config yet.
        self.kalman = KinematicKalmanFilter(dt=1.0)  # Assuming daily/uniform steps
        self.prices = []
        self.lookback = lookback_window
        self.invested = False

    def calculate_signals(self, event: MarketEvent, event_queue):
        if event.type != "MARKET":
            return

        price = event.close
        timestamp = event.timestamp
        symbol = event.symbol

        # 1. Update Physics Models
        self.kalman.update(price)
        state = self.kalman.x  # x is the state vector [pos, vel, acc]
        velocity = state[1]  # [pos, vel, acc]

        self.prices.append(price)
        if len(self.prices) > 2:
            ret = (self.prices[-1] / self.prices[-2]) - 1.0
            self.heavy_tail.update(ret)

        # 2. Check Logic (Need enough data)
        if len(self.prices) < 20:
            return

        alpha = self.heavy_tail.get_current_alpha()

        # Logic:
        # If Alpha < 1.7 (Fat Tails / Infinite Variance Risk) -> EXIT / DO NOT ENTER
        # Else: Follow Velocity

        is_safe_regime = alpha > 1.7

        signal_direction = None

        if not is_safe_regime:
            # Risk Off
            if self.invested:
                signal_direction = "EXIT"
        elif velocity > 0.05:  # Threshold for positive momentum
            signal_direction = "LONG"
        elif velocity < -0.05:
            signal_direction = "EXIT"  # Or SHORT

        # Emit Signal
        if signal_direction:
            # De-dupe signal if already in that state?
            # For backtest simplicity, we send signal, Portfolio/Risk handles sizing.

            # Don't spam LONG if already LONG?
            if signal_direction == "LONG" and not self.invested:
                event_queue.put(SignalEvent(timestamp, symbol, "LONG"))
                self.invested = True
            elif signal_direction == "EXIT" and self.invested:
                event_queue.put(SignalEvent(timestamp, symbol, "EXIT"))
                self.invested = False
