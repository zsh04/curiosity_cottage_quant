import yfinance as yf
import pandas as pd
from typing import Dict, List, Any
from app.data.base import MarketDataProvider


class YahooFinanceProvider(MarketDataProvider):
    """
    Backup Provider using yfinance.
    """

    def __init__(self):
        pass

    def get_bars(
        self, symbol: str, timeframe: str = "1D", limit: int = 100
    ) -> pd.DataFrame:
        # Map timeframe to yfinance interval
        interval = "1d"
        period = "1y"  # Default

        if timeframe == "1H":
            interval = "1h"
        if timeframe == "1Min":
            interval = "1m"

        # Approximate period based on limit
        if limit < 100 and timeframe == "1D":
            period = "6mo"

        try:
            ticker = yf.Ticker(symbol)
            # Fetch history
            df = ticker.history(period=period, interval=interval)

            # Clean up
            if df.empty:
                raise Exception("Yahoo returned empty data")

            df.rename(
                columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                },
                inplace=True,
            )

            return df[["open", "high", "low", "close", "volume"]].tail(limit)

        except Exception as e:
            print(f"Yahoo Data Error: {e}")
            raise e

    def get_current_price(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        # fast check suitable for failover
        # yfinance often has 'currentPrice' or 'regularMarketPrice' in info
        # but fetching .history(period="1d") is often more reliable/fast than .info which scrapes
        df = ticker.history(period="1d", interval="1m")
        if not df.empty:
            return float(df.iloc[-1]["Close"])
        return 0.0

    def get_account_summary(self) -> Dict[str, Any]:
        return {}  # Not applicable

    def get_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        # yfinance can pull news too, could be secondary backup!
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            formatted = []
            for n in news[:limit]:
                formatted.append(
                    {
                        "headline": n.get("title"),
                        "summary": "",  # often empty
                        "url": n.get("link"),
                        "source": n.get("publisher"),
                        "published_at": n.get("providerPublishTime"),
                    }
                )
            return formatted
        except:
            return []
