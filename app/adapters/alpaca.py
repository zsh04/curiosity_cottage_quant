from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
import os
from typing import List, Dict, Any


class AlpacaAdapter:
    """
    Adapter for Alpaca Markets API.
    Handles Market Data and Order Routing.
    """

    def __init__(self, api_key: str = None, secret_key: str = None):
        self.api_key = api_key or os.getenv("APCA_API_KEY_ID")
        self.secret_key = secret_key or os.getenv("APCA_API_SECRET_KEY")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca API Keys (APCA_API_KEY_ID, APCA_API_SECRET_KEY) must be set."
            )

        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)

    def fetch_bars(
        self, symbol: str, start: datetime, end: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical bar data (OHLCV).
        """
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol, timeframe=TimeFrame.Minute, start=start, end=end
        )

        bars = self.data_client.get_stock_bars(request_params)
        df = bars.df

        # Convert to list of dicts for agnostic internal usage
        # Reset index to get 'timestamp' and 'symbol' as columns if they are in index
        df = df.reset_index()
        return df.to_dict(orient="records")

    def get_snapshot(self, symbol: str):
        # Placeholder for Real-time Snapshot logic
        pass
