import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.infra.database.questdb import QuestDBClient


async def check_data():
    print("🔍 Checking QuestDB for historical data...")
    client = QuestDBClient()

    # 1. Show Tables
    print("1. Listing Tables...")
    tables = await client.query("SHOW TABLES")

    if not tables or "dataset" not in tables:
        print("❌ Could not list tables (or empty response).")
    else:
        found_tables = [row[0] for row in tables["dataset"]]
        print(f"   Found Tables: {found_tables}")

        # 2. Check market_ticks
        if "ohlcv_1min" in found_tables:
            print("2. Checking 'ohlcv_1min' count...")
            count_res = await client.query("SELECT count() FROM ohlcv_1min")
            if count_res and "dataset" in count_res:
                count = count_res["dataset"][0][0]
                print(f"   📊 'ohlcv_1min' has {count} rows.")

        if "ohlcv_1d" in found_tables:
            print("3. Checking 'ohlcv_1d' count...")
            count_res = await client.query("SELECT count() FROM ohlcv_1d")
            if count_res and "dataset" in count_res:
                count = count_res["dataset"][0][0]
                print(f"   📊 'ohlcv_1d' has {count} rows.")

        if "market_ticks" in found_tables:
            print("4. Checking 'market_ticks' count...")
            count_res = await client.query("SELECT count() FROM market_ticks")
            if count_res and "dataset" in count_res:
                count = count_res["dataset"][0][0]
                print(f"   📊 'market_ticks' has {count} rows.")

        # 5. Check backtest_events
        if "backtest_events" in found_tables:
            print("5. Checking 'backtest_events' count...")
            count_res = await client.query("SELECT count() FROM backtest_events")
            if count_res and "dataset" in count_res:
                count = count_res["dataset"][0][0]
                print(f"   ℹ️ 'backtest_events' has {count} rows.")


if __name__ == "__main__":
    asyncio.run(check_data())
