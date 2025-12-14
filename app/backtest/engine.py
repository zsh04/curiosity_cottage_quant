import pandas as pd
import numpy as np
import random
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Order:
    id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    limit_price: Optional[float] = None
    timestamp: pd.Timestamp = None


@dataclass
class Trade:
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: pd.Timestamp
    commission: float = 0.0


class EventDrivenBacktester:
    """
    Event-Driven Backtest Engine simulating realistic market conditions.

    Standards:
    - Latency: 100ms delay between Signal and Fill.
    - Slippage: Variable slippage based on Volatility.
    - Partial Fills: Randomly rejecting 10% of limit orders.
    """

    def __init__(self, data: pd.DataFrame, volatility_window: int = 20):
        """
        Args:
            data: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume'].
                  Index must be DatetimeIndex.
            volatility_window: Window size for calculating rolling volatility.
        """
        self.data = data.sort_index()
        self.volatility_window = volatility_window
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self._calculate_volatility()

    def _calculate_volatility(self):
        """Calculate rolling volatility for slippage modeling."""
        # Using simple close-to-close returns volatility
        self.data["returns"] = self.data["Close"].pct_change()
        self.data["volatility"] = (
            self.data["returns"].rolling(window=self.volatility_window).std()
        )

    def process_orders(self, current_time: pd.Timestamp):
        """
        Process pending orders with simulated market microstructure effects.
        """
        fillable_orders = []
        remaining_orders = []

        for order in self.orders:
            # 1. Latency Check: 100ms delay
            # If order was placed at t, it can only be filled at t + 100ms
            if current_time >= order.timestamp + pd.Timedelta(milliseconds=100):
                fillable_orders.append(order)
            else:
                remaining_orders.append(order)

        self.orders = remaining_orders

        # Get current market data
        try:
            # Finding the bar that includes or is closest to current_time
            # For simplicity in this event loop, we assume current_time maps to a bar index
            # In a real event loop, we'd look at the latest quote.
            # Here we use 'asof' to get the latest available price.
            market_data = self.data.iloc[
                self.data.index.get_indexer([current_time], method="pad")[0]
            ]

            # Check if market data time is actually valid (not too old)
            # if market_data.name < current_time - pd.Timedelta(minutes=1): ...

        except IndexError:
            return  # No data found

        current_price = market_data["Close"]
        current_vol = (
            market_data["volatility"] if not pd.isna(market_data["volatility"]) else 0.0
        )

        for order in fillable_orders:
            # 2. Partial Fills / Rejection: 10% chance of rejection
            if random.random() < 0.10:
                print(f"Order {order.id} rejected (simulated partial fill/rejection)")
                continue

            # 3. Slippage Model
            # Slippage is proportional to volatility.
            # Heuristic: slippage = price * volatility * random_factor
            # Direction is usually against the trade (buying higher, selling lower)

            slippage_pct = current_vol * random.uniform(0, 1)  # simple model

            if order.side == "BUY":
                exec_price = current_price * (1 + slippage_pct)
                # Limit check
                if order.limit_price and exec_price > order.limit_price:
                    self.orders.append(order)  # Keep pending
                    continue
            else:
                exec_price = current_price * (1 - slippage_pct)
                # Limit check
                if order.limit_price and exec_price < order.limit_price:
                    self.orders.append(order)  # Keep pending
                    continue

            # Execute Trade
            trade = Trade(
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=exec_price,
                timestamp=current_time,
            )
            self.trades.append(trade)
            print(
                f"Order {order.id} filled at {exec_price:.2f} (Slippage: {slippage_pct * 10000:.1f} bps)"
            )

    def place_order(self, order: Order):
        """Submit an order to the system."""
        if order.timestamp is None:
            order.timestamp = (
                pd.Timestamp.now()
            )  # Should ideally be passed in simulation time
        self.orders.append(order)
