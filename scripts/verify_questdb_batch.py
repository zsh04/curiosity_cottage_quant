import asyncio
import logging
import random
from datetime import datetime, timedelta
from app.dal.backtest import BacktestDAL

# Setup Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("HypatiaTest")


async def main():
    logger.info("🧪 Starting QuestDB Batch Ingestion Test...")
    dal = BacktestDAL()

    run_id = f"BATCH_TEST_{int(datetime.utcnow().timestamp())}"

    # 1. Generate Dummy Equity Curve (1000 points)
    logger.info(f"generating 1000 points for run_id: {run_id}")
    equity_curve = []
    base_equity = 10000.0
    start_time = datetime.utcnow() - timedelta(days=1)

    for i in range(1000):
        change = random.uniform(-10, 15)  # Slight upward drift
        base_equity += change
        drawdown = random.uniform(0, 5)

        point = {
            "timestamp": start_time + timedelta(minutes=i),
            "equity": base_equity,
            "drawdown": drawdown,
        }
        equity_curve.append(point)

    # 2. Ingest Batch
    start_ingest = datetime.utcnow()
    await dal.log_equity_curve(run_id, equity_curve)
    duration = (datetime.utcnow() - start_ingest).total_seconds()
    logger.info(f"⚡ Ingestion took {duration:.4f}s for 1000 rows.")

    # 3. Verify via Query (Wait a moment for QuestDB commit)
    await asyncio.sleep(1.0)

    report = await dal.get_full_report(run_id)
    stored_curve = report.get("equity_curve", [])

    count = len(stored_curve)
    logger.info(f"🔍 Query returned {count} rows.")

    if count == 1000:
        logger.info("✅ SUCCESS: Batch Ingestion Verified.")
    else:
        logger.error(f"❌ FAILURE: Expected 1000 rows, got {count}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
