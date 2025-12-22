import asyncio
import os
import sys
import uuid
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.dal.backtest import BacktestDAL


async def verify_library():
    print("🧪 Verifying Phase 34.2: The Library of Hypatia...")

    dal = BacktestDAL()
    run_id = f"test_run_{uuid.uuid4().hex[:8]}"
    ticker = "AAPL"

    print(f"1. Spawning Run: {run_id}")
    await dal.log_spawn(run_id, ticker, {"mode": "test", "capital": 100000})

    print("2. Logging Equity Snapshot...")
    await dal.log_equity_snapshot(run_id, 100000.0, 0.0, datetime.utcnow())
    await asyncio.sleep(0.1)  # ensure timestamp diff
    await dal.log_equity_snapshot(run_id, 100500.0, 0.0, datetime.utcnow())

    print("3. Logging Completion...")
    await dal.log_completion(run_id, ticker, {"sharpe": 2.5, "return": 0.005})

    # Allow some time for ILP ingestion (async/UDP/TCP buffers)
    print("⏳ Waiting for Ingest (1s)...")
    await asyncio.sleep(1)

    print("4. Reading Run Status (Expected: COMPLETED)...")
    status = await dal.get_run_status(run_id)
    print(f"-> Status: {status}")

    if status != "COMPLETED":
        print(
            "❌ Verification FAILED: Status mismatch (Ensure QuestDB is running and Schema is applied)"
        )
        return

    print("5. fetching Full Report...")
    report = await dal.get_full_report(run_id)
    events = report["events"]
    equity = report["equity_curve"]

    print(f"-> Events Found: {len(events)}")
    print(f"-> Equity Points: {len(equity)}")

    if len(events) >= 2 and len(equity) >= 2:
        print("✅ FULL SUCCESS: Event Sourcing Operational.")
    else:
        print("⚠️ PARTIAL SUCCESS: Data might be buffered or missing.")


if __name__ == "__main__":
    asyncio.run(verify_library())
