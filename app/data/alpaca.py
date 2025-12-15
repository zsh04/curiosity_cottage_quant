import os
import pandas as pd
from typing import Dict, List, Any
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from app.data.base import MarketDataProvider
from datetime import datetime, timedelta


class AlpacaProvider(MarketDataProvider):
    """
    Concrete implementation for Alpaca Markets.
    """

    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.api_secret = os.getenv("ALPACA_API_SECRET")
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

        self.trading_client = TradingClient(self.api_key, self.api_secret, paper=True)
        self.data_client = StockHistoricalDataClient(self.api_key, self.api_secret)

    def get_bars(
        self, symbol: str, timeframe: str = "1D", limit: int = 100
    ) -> pd.DataFrame:
        tf = TimeFrame.Day
        if timeframe == "1H":
            tf = TimeFrame.Hour
        elif timeframe == "1Min":
            tf = TimeFrame.Minute

        # Determine start time based on limit (approx)
        # Assuming 1D bars, start = now - limit * 1.5 days to be safe
        start_time = datetime.now() - timedelta(days=limit * 1.5)

        request = StockBarsRequest(
            symbol_or_symbols=symbol, timeframe=tf, start=start_time, limit=limit
        )

        try:
            bars = self.data_client.get_stock_bars(request)
            df = bars.df
            # Standardize columns: open, high, low, close, volume
            # Alpaca df usually has MultiIndex (symbol, timestamp) or just timestamp
            if isinstance(df.index, pd.MultiIndex):
                df = df.droplevel(0)  # Drop symbol level

            # Ensure index is datetime and localized? Alpaca gives UTC.
            # Convert to relevant columns
            df = df[["open", "high", "low", "close", "volume"]]
            return df
        except Exception as e:
            print(f"Alpaca Data Error: {e}")
            raise e

    def get_current_price(self, symbol: str) -> float:
        # For simplicity, getting latest bar or quote
        # Using get_bars for now with limit 1
        df = self.get_bars(symbol, limit=1)
        if not df.empty:
            return float(df.iloc[-1]["close"])
        return 0.0

    def get_account_summary(self) -> Dict[str, Any]:
        acct = self.trading_client.get_account()
        return {
            "equity": float(acct.equity),
            "buying_power": float(acct.buying_power),
            "cash": float(acct.cash),
            "status": acct.status,
        }

    def get_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        # Alpaca has news API but let's leave this for Finnhub per plan
        return []
