import os
import sys
import logging
from datetime import datetime
import pandas as pd
import yfinance as yf
from questdb.ingress import Sender, IngressError, TimestampNanos
from tqdm import tqdm
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load Environment
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | BACKFILL_MACRO | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backfill_macro")

# --- Configuration ---
QDB_HOST = "localhost"
QDB_PORT = 9000

# --- Universe Definition (Tier 2 - Macro) ---
SECTORS = ["XLF", "XLK", "XLY", "XLC", "XLV", "XLB", "XLU", "XLI", "XLE", "XLRE"]
ASSETS = ["AGG", "LQD", "HYG", "USO", "SLV"]
# Yahoo Tickers for Indices often start with ^
INDICES = ["^VIX", "^TNX", "DX-Y.NYB", "^GSPC", "^NDX"]
BENCHMARKS = ["RSP", "QQEW", "SPGI"]

# Tier 1 Universe (Redefined here for standalone execution)
TIER1_INDICES = ["SPY", "QQQ", "IWM"]
TIER1_MAG_7 = [
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
TIER1_MOMENTUM = ["SMH", "ARKK", "COIN", "MSTR"]
TIER1_PROXIES = ["VIXY", "GLD", "TLT", "UUP"]

TIER1_FULL = TIER1_INDICES + TIER1_MAG_7 + TIER1_MOMENTUM + TIER1_PROXIES

# Complete Macro Universe
UNIVERSE = list(set(SECTORS + ASSETS + INDICES + BENCHMARKS + TIER1_FULL))


def run_backfill(test_mode: bool = False):
    """
    Main Execution Function for Tier 2 Backfill.
    """
    logger.info("🚀 STARTING TIER 2 BACKFILL (MACRO - 1 DAY) 🚀")
    logger.info(f"Universe Size: {len(UNIVERSE)}")
    logger.info(f"QuestDB: {QDB_HOST}:{QDB_PORT}")

    # Configuration for yfinance
    period = "20y"
    if test_mode:
        period = "1mo"
        logger.info("🧪 TEST MODE: Fetching 1 month of data")

    # 1. Bulk Download from Yahoo Finance
    logger.info("📥 Downloading data from Yahoo Finance...")
    try:
        # group_by='ticker' makes columns (Ticker, OHLCV)
        # auto_adjust=True handles splits/dividends
        data = yf.download(
            tickers=UNIVERSE,
            period=period,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=True,
        )
    except Exception as e:
        logger.error(f"❌ Failed to download data: {e}")
        return

    if data.empty:
        logger.error("❌ No data downloaded!")
        return

    logger.info("✅ Download Complete. Processing & Ingesting...")

    # 2. Ingest to QuestDB
    conf = f"http::addr={QDB_HOST}:{QDB_PORT};"

    try:
        with Sender.from_conf(conf) as sender:
            # Iterate through each ticker in the universe
            # Note: yf.download might drop tickers that failed, so we check columns

            # If only 1 ticker is returned, data columns are just OHLCV, not MultiIndex
            # But with len(UNIVERSE) > 1, it should be MultiIndex.
            # Handle edge case where Universe size might be small in testing if modified.

            is_multi_index = isinstance(data.columns, pd.MultiIndex)

            tickers_to_process = UNIVERSE if is_multi_index else [UNIVERSE[0]]

            # Filter tickers that are actually in the columns
            if is_multi_index:
                # Top level of columns is Ticker
                available_tickers = data.columns.levels[0]
                tickers_to_process = [
                    t for t in tickers_to_process if t in available_tickers
                ]

            pbar = tqdm(tickers_to_process, desc="Ingesting", unit="ticker")

            for ticker in pbar:
                pbar.set_postfix(ticker=ticker)

                try:
                    # Extract dataframe for this ticker
                    if is_multi_index:
                        df_ticker = data[ticker].copy()
                    else:
                        df_ticker = data.copy()

                    # Drop rows with all NaNs (common in bulk downloads)
                    df_ticker.dropna(how="all", inplace=True)

                    if df_ticker.empty:
                        logger.warning(f"⚠️ Empty data for {ticker}")
                        continue

                    # Reset index to get Date column
                    df_ticker.reset_index(inplace=True)

                    # Ensure columns exist (Case sensitivity varies by yf version)
                    # YF usually returns: Open, High, Low, Close, Volume (Title Case)
                    # We map them to lowercase for QuestDB

                    # Columns might be 'Date', 'Open', 'High', etc.

                    rows_ingested = 0
                    for _, row in df_ticker.iterrows():
                        date_val = row.get("Date")
                        if pd.isnull(date_val):
                            continue

                        # Convert to nanoseconds
                        ts_nanos = TimestampNanos.from_datetime(
                            date_val.to_pydatetime()
                        )

                        # Handle potential NaNs in rows
                        op = row.get("Open")
                        hi = row.get("High")
                        lo = row.get("Low")
                        cl = row.get("Close")
                        vo = row.get("Volume")

                        if any(pd.isnull(x) for x in [op, hi, lo, cl]):
                            continue

                        sender.row(
                            "ohlcv_1d",
                            symbols={"symbol": ticker, "exchange": "YFINANCE"},
                            columns={
                                "open": float(op),
                                "high": float(hi),
                                "low": float(lo),
                                "close": float(cl),
                                "volume": int(vo) if not pd.isnull(vo) else 0,
                            },
                            at=ts_nanos,
                        )
                        rows_ingested += 1

                    # Flush per ticker or less frequently?
                    # Sender buffers, but flushing per ticker is safe to avoid huge buffers.
                    sender.flush()

                except Exception as e:
                    logger.error(f"❌ Error processing {ticker}: {e}")
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
        "--test", action="store_true", help="Run in test mode (1 month data)"
    )
    args = parser.parse_args()

    run_backfill(test_mode=args.test)
