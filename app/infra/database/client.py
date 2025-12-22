import asyncio
import pandas as pd
from datetime import datetime
from typing import Optional
from app.infra.database.questdb import QuestDBClient


class TimescaleClient:
    """
    Client for querying market data from QuestDB (formerly TimescaleDB).
    Kept class name for backward compatibility until full refactor.
    Uses 'ohlcv_1min' table.
    """

    def __init__(self):
        self.client = QuestDBClient()

    async def _fetch_bars_async(
        self, symbol: str, start_date: datetime, end_date: datetime
    ):
        # Format dates for QuestDB SQL (ISO 8601 usually works, or 'YYYY-MM-DDTHH:mm:ss.SSSSSSZ')
        # QuestDB timestamps in WHERE clause prefer strings or specific formats.
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        query = f"""
        SELECT ts as time, open, high, low, close, volume
        FROM ohlcv_1min
        WHERE symbol = '{symbol}'
        AND ts >= '{start_str}'
        AND ts <= '{end_str}'
        ORDER BY ts ASC
        """

        result = await self.client.query(query)
        if not result or "dataset" not in result:
            return []

        columns = [c["name"] for c in result["columns"]]
        rows = result["dataset"]
        # Convert list of lists to dicts for DataFrame compat (or just return rows/cols)
        return [dict(zip(columns, row)) for row in rows]

    def get_bars(
        self, symbol: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """
        Synchronous wrapper to fetch bars as a Pandas DataFrame.
        """
        rows = asyncio.run(self._fetch_bars_async(symbol, start_date, end_date))

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        # QuestDB returns ISO strings for timestamps, convert them
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        # Ensure numeric types
        cols = ["open", "high", "low", "close", "volume"]
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c])

        return df
