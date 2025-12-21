import os
import sys
import logging
from datetime import datetime
from tqdm import tqdm
from questdb.ingress import Sender, IngressError, TimestampNanos
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load Environment
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | BACKFILL | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backfill")

# --- Configuration ---
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET")
# QDB ILP Host
QDB_HOST = "localhost"
QDB_PORT = 9000

# --- Universe Definition (Tier 1) ---
INDICES = ["SPY", "QQQ", "IWM"]
MAG_7 = [
    "NVDA",
    "TSLA",
    "AAPL",
    "AMD",
    "MSFT",
    "META",
    "GOOGL",
    "AMZN",
    "NFLX",
    "JPM",
    "SHOP",
    "BA",
]
MOMENTUM_RISK = ["SMH", "ARKK", "COIN", "MSTR"]
PROXIES = ["VIXY", "GLD", "TLT", "UUP"]

UNIVERSE = list(set(INDICES + MAG_7 + MOMENTUM_RISK + PROXIES))


def run_backfill(test_mode: bool = False):
    """
    Main Execution Function.
    """
    logger.info("🚀 STARTING TIER 1 BACKFILL (MICRO - 1 MIN) 🚀")
    logger.info(f"Universe Size: {len(UNIVERSE)}")
    logger.info(f"QuestDB: {QDB_HOST}:{QDB_PORT}")

    if not ALPACA_API_KEY or not ALPACA_API_SECRET:
        logger.error("❌ Alpaca Keys Missing! Check .env")
        return

    # 1. Initialize Clients
    client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)

    # 2. Iterate Universe
    # Use tqdm for progress bar
    pbar = tqdm(UNIVERSE, desc="Processing Symbols", unit="ticker")

    # Establish QuestDB Connection (Sender is context manager)
    # We open a new sender for the whole batch or per symbol?
    # Usually one sender is fine, but for robustness let's do per symbol or handle errors.
    # Official docs suggest reusing sender.

    conf = f"http::addr={QDB_HOST}:{QDB_PORT};"

    try:
        with Sender.from_conf(conf) as sender:
            for symbol in pbar:
                pbar.set_postfix(symbol=symbol)

                # Fetch Data
                start_date = datetime(2016, 1, 1)
                end_date = datetime.now()

                if test_mode:
                    # Fetch only last 2 days for test
                    start_date = datetime.now().replace(
                        year=datetime.now().year,
                        month=datetime.now().month,
                        day=datetime.now().day,
                    )
                    # Actually just make it simple, last 5 days
                    from datetime import timedelta

                    start_date = datetime.now() - timedelta(days=5)

                req = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Minute,
                    start=start_date,
                    end=end_date,
                )

                try:
                    # Alpaca SDK handles pagination internally
                    bars = client.get_stock_bars(req)

                    if bars.df.empty:
                        logger.warning(f"⚠️ No data for {symbol}")
                        continue

                    df = bars.df
                    # Reset index to get timestamp as column if it's index
                    if "timestamp" not in df.columns:
                        df = df.reset_index()

                    # Ensure we have data for this symbol (dataframe might contain other symbols if request was multi)
                    # specifically SDK returns MultiIndex (symbol, timestamp) usually

                    # Convert to rows
                    # We can iterate the dataframe

                    row_count = 0
                    for index, row in df.iterrows():
                        # Index is likely (symbol, timestamp) or just timestamp depending on how it was reset
                        # If we reset_index(), 'symbol' and 'timestamp' are columns

                        ts = row["timestamp"]
                        # Convert to nanoseconds for QuestDB?
                        # Sender expects datetime object or explicit nanos.
                        # Pandas timestamp is usually fine if we convert.

                        # Use TimestampNanos for precision
                        ts_nanos = TimestampNanos.from_datetime(ts.to_pydatetime())

                        sender.row(
                            "ohlcv_1min",
                            symbols={
                                "symbol": symbol,
                                "exchange": "ALPACA",  # Default exchange tag
                            },
                            columns={
                                "open": float(row["open"]),
                                "high": float(row["high"]),
                                "low": float(row["low"]),
                                "close": float(row["close"]),
                                "volume": int(row["volume"]),
                            },
                            at=ts_nanos,
                        )
                        row_count += 1

                    # Send batch
                    sender.flush()

                    # logger.info(f"✅ {symbol}: Ingested {row_count} rows")

                except Exception as e:
                    logger.error(f"❌ Error processing {symbol}: {e}")
                    continue

    except IngressError as e:
        logger.error(f"❌ QuestDB Ingress Error: {e}")
    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error(f"❌ Critical Backfill Error: {e}")

    logger.info("🏁 BACKFILL COMPLETE 🏁")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test", action="store_true", help="Run in test mode (fewer days)"
    )
    args = parser.parse_args()

    run_backfill(test_mode=args.test)
