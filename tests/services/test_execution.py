import pytest
from unittest.mock import MagicMock
from datetime import datetime
from app.core.models import TradeSignal, Side, OrderPacket
from app.services.execution import ExecutionService


@pytest.fixture
def mock_alpaca():
    client = MagicMock()
    # Mock submit_order return
    mock_order = MagicMock()
    mock_order.id = "test-order-id"
    mock_order.symbol = "BTC"
    mock_order.side.value = "buy"
    mock_order.status.value = "new"
    mock_order.qty = 0.5
    mock_order.filled_avg_price = None
    client.submit_order.return_value = mock_order
    return client


@pytest.fixture
def execution_service(mock_alpaca):
    return ExecutionService(starting_nav=1000.0, broker_client=mock_alpaca)


def test_veto_logic_hold(execution_service):
    """
    Test that HOLD signal is ignored.
    """
    signal = TradeSignal(
        timestamp=datetime.now(),
        symbol="BTC",
        side=Side.HOLD,
        strength=0.0,
        price=50000.0,
    )
    order = execution_service.veto_and_size(signal)
    assert order is None


def test_sizing_logic_default(execution_service):
    """
    Test default 1% sizing.
    """
    signal = TradeSignal(
        timestamp=datetime.now(), symbol="BTC", side=Side.BUY, strength=0.8, price=100.0
    )
    # NAV=1000. 1% = $10. Price=100. Qty = 0.1
    order = execution_service.veto_and_size(signal)

    assert order is not None
    assert order.symbol == "BTC"
    assert order.side == "BUY"
    assert order.quantity == pytest.approx(0.1)
    assert order.risk_check_passed is True


def test_sizing_logic_override(execution_service):
    """
    Test quantity override in signal.
    """
    signal = TradeSignal(
        timestamp=datetime.now(),
        symbol="BTC",
        side=Side.SELL,
        strength=0.9,
        price=50000.0,
        quantity=0.5,
    )
    order = execution_service.veto_and_size(signal)

    assert order is not None
    assert order.quantity == 0.5


def test_ruin_constraint(execution_service):
    """
    Test that trading stops if daily loss exceeds threshold.
    """
    # Threshold is 2% of 1000 = $20.
    execution_service.daily_pnl = -21.0

    signal = TradeSignal(
        timestamp=datetime.now(), symbol="BTC", side=Side.BUY, strength=0.8, price=100.0
    )
    order = execution_service.veto_and_size(signal)
    assert order is None  # Rejected


def test_execute_order_calls_alpaca(execution_service, mock_alpaca):
    """
    Test that execute_order calls the broker client correctly.
    """
    order = OrderPacket(
        timestamp=datetime.now(),
        signal_id="123",
        symbol="BTC",
        side="BUY",
        quantity=0.5,
        order_type="MARKET",
        risk_check_passed=True,
    )

    report = execution_service.execute_order(order)

    # Check Alpaca call
    mock_alpaca.submit_order.assert_called_once()
    call_args = mock_alpaca.submit_order.call_args[1]
    assert call_args["symbol"] == "BTC"
    assert call_args["qty"] == 0.5
    assert call_args["side"] == "BUY"

    # Check Report
    assert report.order_id == "test-order-id"
    assert report.status == "NEW"
    assert report.symbol == "BTC"
