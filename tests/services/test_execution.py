import pytest
from datetime import datetime
from app.services.execution import ExecutionService
from app.core.models import TradeSignal, Side


class TestTalebGatekeeper:
    @pytest.fixture
    def gatekeeper(self):
        # Default $500 NAV, 2% Stop ($10.00)
        return ExecutionService()

    @pytest.fixture
    def buy_signal(self):
        return TradeSignal(
            timestamp=datetime.now(),
            symbol="BTC-USD",
            side=Side.BUY,
            strength=1.0,
            price=50000.0,
            meta={},
        )

    def test_normal_execution(self, gatekeeper, buy_signal):
        """Case A: Normal Buy."""
        order = gatekeeper.veto_and_size(buy_signal)

        assert order is not None
        assert order.risk_check_passed is True
        assert order.symbol == "BTC-USD"

        # Sizing Check: 1% of $500 = $5.00.
        # Price = 50,000.
        # Qty = 5 / 50000 = 0.0001
        assert order.quantity == pytest.approx(0.0001)

    def test_ruin_constraint(self, gatekeeper, buy_signal):
        """Case B: Hard Stop Breached."""
        # Simulate Ruin: Loss of $11.00 (Limit is $10.00)
        gatekeeper.daily_pnl = -11.0

        order = gatekeeper.veto_and_size(buy_signal)

        assert order is None
        # Logs should show "REJECTED"

    def test_hold_ignored(self, gatekeeper, buy_signal):
        """Case C: Hold Signal."""
        buy_signal.side = Side.HOLD

        order = gatekeeper.veto_and_size(buy_signal)

        assert order is None
