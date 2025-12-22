import asyncio
import os
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.getcwd())

from app.infra.database.questdb import QuestDBClient


async def seed_questdb():
    print("🌱 Seeding QuestDB from YFinance...")
    client = QuestDBClient()
    symbol = "SPY"  # Default test symbol

    print(f"1. Fetching Data for {symbol}...")
    # Fetch 5 days of 1-minute data for OHLCV
    ohlc = yf.download(symbol, period="5d", interval="1m", progress=False)

    if ohlc.empty:
        print("❌ No data found.")
        return

    print(f"   Received {len(ohlc)} OHLCV records.")

    # QUESTDB INGESTION
    print("2. Ingesting to 'ohlcv_1min' (ILP)...")
    count = 0
    for ts, row in ohlc.iterrows():
        # Ensure TS is UTC datetime
        if not isinstance(ts, datetime):
            # Depending on pandas version, index might be Timestamp
            ts = ts.to_pydatetime()

        # YFinance rows are multi-index usually if multi-ticker, but simple here
        # Accessing might be tricky with new yfinance versions -> row['Close'].iloc[0] if specific
        # For simple download:
        try:
            op = float(row["Open"])
            hi = float(row["High"])
            lo = float(row["Low"])
            cl = float(row["Close"])
            vo = float(row["Volume"])
        except Exception:
            # Handle Scalar/Series ambiguity
            op = (
                float(row["Open"].iloc[0])
                if hasattr(row["Open"], "iloc")
                else float(row["Open"])
            )
            hi = (
                float(row["High"].iloc[0])
                if hasattr(row["High"], "iloc")
                else float(row["High"])
            )
            lo = (
                float(row["Low"].iloc[0])
                if hasattr(row["Low"], "iloc")
                else float(row["Low"])
            )
            cl = (
                float(row["Close"].iloc[0])
                if hasattr(row["Close"], "iloc")
                else float(row["Close"])
            )
            vo = (
                float(row["Volume"].iloc[0])
                if hasattr(row["Volume"], "iloc")
                else float(row["Volume"])
            )

        # Log OHLCV
        await client.ingest_ilp(
            table_name="ohlcv_1min",
            symbols={"symbol": symbol},
            columns={"open": op, "high": hi, "low": lo, "close": cl, "volume": vo},
            timestamp=ts,
        )

        # Verify: Log a "Tick" for every minute (Simulation)
        # 'market_ticks' is usually higher freq, but we'll map the close as a trade
        await client.ingest_ilp(
            table_name="market_ticks",
            symbols={
                "symbol": symbol,
                "side": "buy" if cl > op else "sell",
                "condition": "auto",
            },
            columns={"price": cl, "volume": vo},
            timestamp=ts,
        )
        count += 1
        if count % 100 == 0:
            print(f"   ... processed {count} rows")

    print(f"✅ Ingestion Complete. {count} rows sent via ILP.")


if __name__ == "__main__":
    asyncio.run(seed_questdb())
