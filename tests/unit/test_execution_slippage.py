import pytest
import numpy as np
from app.backtest.execution import FrictionExecution
from app.backtest.events import OrderEvent, MarketEvent
from datetime import datetime


class TestPredatorySlippage:
    def test_predatory_slippage_impact(self):
        """
        Verify that providing volatile recent ticks increases slippage cost.
        """
        exec_model = FrictionExecution(spread_bps=5.0, impact_factor=0.1)

        order = OrderEvent(
            symbol="TEST",
            quantity=100,
            direction="BUY",
            order_type="MARKET",
            timestamp=datetime.now(),
        )
        market = MarketEvent(
            timestamp=datetime.now(),
            symbol="TEST",
            close=100.0,
            volume=1000,
            open=99.0,
            high=101.0,
            low=99.0,
        )

        # 1. Baseline Fill (No Ticks)
        fill_price_base, _ = exec_model.simulate_fill(order, market)
        slippage_base = (fill_price_base / 100.0) - 1.0

        # 2. Predatory Fill (High Local Vol)
        # Std dev of [90, 110, 90...] is ~10.0
        recent_ticks = [90.0 if i % 2 == 0 else 110.0 for i in range(20)]

        fill_price_predatory, _ = exec_model.simulate_fill(
            order, market, recent_ticks=recent_ticks
        )
        slippage_pred = (fill_price_predatory / 100.0) - 1.0

        print(f"Base Slip: {slippage_base * 10000:.2f} bps")
        print(f"Pred Slip: {slippage_pred * 10000:.2f} bps")

        assert fill_price_predatory > fill_price_base
        assert slippage_pred > slippage_base * 1.2  # Significant increase
