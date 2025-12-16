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
            if not settings.ALPACA_API_KEY or not settings.ALPACA_SECRET_KEY:
                logger.warning(
                    "⚠️ Alpaca Keys missing despite LIVE_TRADING_ENABLED=True"
                )
                return

            try:
                self.client = TradingClient(
                    api_key=settings.ALPACA_API_KEY,
                    secret_key=settings.ALPACA_SECRET_KEY,
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
    ):
        """
        Submit a Market Order.
        """
        if not self.client:
            raise RuntimeError(
                "Alpaca Client not initialized (Keys missing or Init failed)"
            )

        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
            time_in_force=time_in_force,
        )

        return self.client.submit_order(req)
