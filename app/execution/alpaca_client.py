from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class AlpacaClient:
    """
    Wrapper for Alpaca Trading Client.
    """

    def __init__(self):
        self._enabled = settings.LIVE_TRADING_ENABLED
        self.client = None

        if self._enabled:
            # Only initialize if enabled/configured to avoid errors in dev/backtest
            if not settings.ALPACA_API_KEY or not settings.ALPACA_API_SECRET:
                logger.warning(
                    "⚠️ Alpaca Keys missing despite LIVE_TRADING_ENABLED=True"
                )
                return

            try:
                self.client = TradingClient(
                    api_key=settings.ALPACA_API_KEY,
                    secret_key=settings.ALPACA_API_SECRET,
                    paper=(
                        "paper" in settings.ALPACA_ENDPOINT
                        or "sandbox" in settings.ALPACA_ENDPOINT
                    ),
                )
            except Exception as e:
                logger.error(f"❌ Failed to init Alpaca TradingClient: {e}")

    def get_account(self):
        """
        Fetch Account information (Cash, Buying Power, Unsettled Funds).
        """
        if not self.client:
            if self._enabled:
                logger.error("Alpaca Client not initialized caught in get_account")
            return None

        try:
            return self.client.get_account()
        except Exception as e:
            logger.error(f"Failed to fetch account info: {e}")
            return None

    async def get_account_async(self):
        """
        Async wrapper for get_account.
        """
        if not self.client:
            return None

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_account)

    def submit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: float = None,  # NEW: Limit Price Support
    ):
        """
        Submit a Market or Limit Order.
        """
        if not self.client:
            raise RuntimeError(
                "Alpaca Client not initialized (Keys missing or Init failed)"
            )

        target_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

        if limit_price and limit_price > 0:
            # Limit Order
            from alpaca.trading.requests import LimitOrderRequest

            req = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=target_side,
                time_in_force=time_in_force,
                limit_price=limit_price,
            )
        else:
            # Market Order (Fallback)
            req = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=target_side,
                time_in_force=time_in_force,
            )

        return self.client.submit_order(req)

    async def submit_order_async(self, **kwargs):
        """
        Async wrapper for submit_order to prevent blocking the Event Loop.
        Uses ThreadPoolExecutor to offload the I/O.
        """
        if not self.client:
            # If disabled, maybe simulate slightly async delay?
            # Or just call synchronous for simulation which is fast.
            if not self._enabled:
                return self.submit_order(**kwargs)

            raise RuntimeError("Alpaca Client not initialized")

        loop = asyncio.get_running_loop()
        # Pass keyword arguments to submit_order via lambda or partial?
        # partial is cleaner.
        from functools import partial

        return await loop.run_in_executor(None, partial(self.submit_order, **kwargs))

    def list_positions(self):
        """
        Get all open positions.
        """
        if not self.client:
            if self._enabled:
                logger.error("Alpaca Client not initialized caught in list_positions")
            return []

        try:
            return self.client.get_all_positions()
        except Exception as e:
            logger.error(f"Failed to list positions: {e}")
            return []

    def get_positions(self):
        """
        Alias for list_positions for compatibility.
        """
        return self.list_positions()
