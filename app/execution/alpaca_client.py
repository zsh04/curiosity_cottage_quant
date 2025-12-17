from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from app.core.config import settings
import logging

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
