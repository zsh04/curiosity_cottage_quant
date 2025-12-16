#!/usr/bin/env python3
import os
import sys
import pandas as pd
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from dotenv import load_dotenv

import yfinance as yf

# Add project root to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / ".venv/lib/python3.14/site-packages"))  # Just in case

# Load .env
load_dotenv(root_dir / ".env")

# Force IPv4 for local connection
os.environ["DATABASE_URL"] = "postgresql://postgres:password@127.0.0.1:5432/quant_db"

from app.dal.database import get_db
from app.dal.models import MarketTick


def seed_data():
    print("🌱 Seeding Database with SPY data from yfinance...")

    symbol = "SPY"

    # Fetch Data
    print(f"   Fetching 1 year of history for {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d")
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        return

    if df.empty:
        print("❌ No data returned from yfinance")
        return

    print(f"   Received {len(df)} records.")
    print(f"   Range: {df.index[0]} to {df.index[-1]}")

    # Database Session
    db: Session = next(get_db())

    # Insert Data
    print("   Inserting into TimescaleDB...")
    count = 0

    for timestamp, row in df.iterrows():
        # yfinance timestamp is timezone aware (usually America/New_York)
        # We convert to UTC for consistency
        ts_utc = timestamp.astimezone(timezone.utc)

        # Check if exists
        existing = (
            db.query(MarketTick)
            .filter(MarketTick.symbol == symbol, MarketTick.time == ts_utc)
            .first()
        )

        if not existing:
            tick = MarketTick(
                time=ts_utc,
                symbol=symbol,
                price=float(row["Close"]),  # Legacy field
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
            )
            db.add(tick)
            count += 1

    db.commit()
    print(f"✅ Successfully inserted {count} new ticks.")
    db.close()


if __name__ == "__main__":
    seed_data()
