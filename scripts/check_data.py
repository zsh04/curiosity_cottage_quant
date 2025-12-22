#!/usr/bin/env python3.11
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["DATABASE_URL"] = "postgresql://postgres:password@127.0.0.1:5432/quant_db"

from app.dal.database import get_db
from app.dal.models import MarketTick
from datetime import datetime, timedelta

db = next(get_db())
count = db.query(MarketTick).count()
print(f"Total ticks in database: {count}")

if count > 0:
    first_ticker = db.query(MarketTick.symbol).first()
    print(f"Example symbol: {first_ticker[0]}")

if count > 0:
    latest = (
        db.query(MarketTick)
        .filter(MarketTick.symbol == "SPY")
        .order_by(MarketTick.time.desc())
        .first()
    )
    print(f"Latest tick: {latest.time} @ ${latest.close}")

    earliest = (
        db.query(MarketTick)
        .filter(MarketTick.symbol == "SPY")
        .order_by(MarketTick.time)
        .first()
    )
    print(f"Earliest tick: {earliest.time} @ ${earliest.close}")
else:
    print("No SPY data found!")

db.close()
