import asyncio
import os
import asyncpg
import pandas as pd
from datetime import datetime


class TimescaleClient:
    """
    Client for querying market data from TimescaleDB.
    """

    def __init__(self, dsn: str = None):
        self.dsn = dsn or os.getenv(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/quant_db"
        )

    async def _fetch_bars_async(
        self, symbol: str, start_date: datetime, end_date: datetime
    ):
        conn = await asyncpg.connect(self.dsn)
        try:
            rows = await conn.fetch(
                """
                SELECT time, open, high, low, close, volume 
                FROM market_bars 
                WHERE symbol = $1 
                AND time >= $2 
                AND time <= $3
                ORDER BY time ASC
            """,
                symbol,
                start_date,
                end_date,
            )
            return rows
        finally:
            await conn.close()

    def get_bars(
        self, symbol: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """
        Synchronous wrapper to fetch bars as a Pandas DataFrame.
        """
        rows = asyncio.run(self._fetch_bars_async(symbol, start_date, end_date))

        if not rows:
            return pd.DataFrame()

        data = [dict(row) for row in rows]
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        return df
