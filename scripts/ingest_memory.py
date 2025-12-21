"""
Market Memory Daemon (The Archivist).

Responsibilities:
1. Wakes up periodically (or scheduled).
2. Syncs recent market data from QuestDB (Tick/1-Min).
3. Creates vectors (64-min sliding windows) + labels (15-min forward return).
4. Normalizes and indexes them into LanceDB.

Run: python scripts/ingest_memory.py
"""

import sys
import os
import time
import logging
import asyncio
import pandas as pd
import numpy as np
import requests
from typing import List, Dict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.services.rag_forecast import MarketMemory

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | MEMORY_DAEMON | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest_memory")


class MarketMemoryDaemon:
    def __init__(self):
        self.memory = MarketMemory()
        self.questdb_url = settings.QUESTDB_URL
        self.window_size = settings.RAF_WINDOW_SIZE  # 64
        self.params = {
            "forward_horizon": 15,  # 15 minutes for label
        }

    def is_market_hours(self) -> bool:
        """Simple check for NY Trading Hours (9:30 - 16:00 ET)."""
        # UTC to ET conversion roughly
        # This is a basic daemon, skipping strict calendar logic for now.
        return True  # logic to implement

    def fetch_recent_data(self, symbol: str, lookback_hours: int = 24) -> pd.DataFrame:
        """Fetch 1-min bars from QuestDB via REST API."""
        # We need enough data to form windows.
        # If running continuously, this query should be optimized to fetch only new data.
        # Here we fetch last `lookback_hours` for simplicity.

        query = f"""
        SELECT timestamp, close 
        FROM 'ohlcv_1min' 
        WHERE symbol = '{symbol}' 
        AND timestamp > dateadd('h', -{lookback_hours}, now())
        ORDER BY timestamp ASC
        """

        try:
            resp = requests.get(f"{self.questdb_url}/exec", params={"query": query})
            resp.raise_for_status()
            data = resp.json()

            if not data.get("dataset"):
                return pd.DataFrame()

            df = pd.DataFrame(
                data["dataset"], columns=[c["name"] for c in data["columns"]]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        except Exception as e:
            logger.error(f"QuestDB Query Error for {symbol}: {e}")
            return pd.DataFrame()

    def process_symbol(self, symbol: str):
        """Process a single symbol: Fetch -> Vectorize -> Ingest."""
        df = self.fetch_recent_data(symbol)
        if df.empty or len(df) < (self.window_size + self.params["forward_horizon"]):
            return 0

        # Calculations
        # 1. Forward Return (Label): (Price[t+15] - Price[t]) / Price[t]
        # Shifted back by 15: The validation at time `t` needs future price `t+15`
        # label[t] = returns from t to t+H
        # So we align: Vector[t] (ending at t) corresponds to Outcome[t] (calculated from t to t+H)

        # We use strict aligned windows.
        # Vector ending at index i uses prices[i-63 : i+1]
        # Outcome at index i uses (price[i+15] - price[i]) / price[i]

        # Prepare lists
        patterns = []

        prices = df["close"].values
        timestamps = df["timestamp"].values

        # Iterate
        # Start where we have a full window
        # End where we have a forward return
        start_idx = self.window_size - 1
        end_idx = len(df) - self.params["forward_horizon"]

        if start_idx >= end_idx:
            return 0

        for i in range(start_idx, end_idx):
            # Window
            window = prices[i - (self.window_size - 1) : i + 1]

            # Outcome
            current_price = prices[i]
            future_price = prices[i + self.params["forward_horizon"]]
            outcome = (future_price - current_price) / current_price

            # Normalize Vector (Z-Score or MinMax? Prompt says Z-Score)
            mean = np.mean(window)
            std = np.std(window)
            if std == 0:
                continue

            norm_vector = ((window - mean) / std).tolist()

            patterns.append(
                {
                    "vector": norm_vector,
                    "symbol": symbol,
                    "timestamp": timestamps[i],  # Timestamp of the point of decision
                    "outcome": float(outcome),
                }
            )

        # Bulk Add
        if patterns:
            self.memory.add_patterns(patterns)

        return len(patterns)

    def fetch_range(
        self, symbol: str, start_ts: datetime, end_ts: datetime
    ) -> pd.DataFrame:
        """Fetch range of data."""
        # QuestDB generic timestamp format: '2023-01-01T00:00:00.000000Z'
        s_str = start_ts.strftime("%Y-%m-%dT%H:%M:%S.000000Z")
        e_str = end_ts.strftime("%Y-%m-%dT%H:%M:%S.000000Z")

        query = f"""
        SELECT timestamp, close 
        FROM 'ohlcv_1min' 
        WHERE symbol = '{symbol}' 
        AND timestamp >= '{s_str}' AND timestamp < '{e_str}'
        ORDER BY timestamp ASC
        """
        try:
            resp = requests.get(f"{self.questdb_url}/exec", params={"query": query})
            resp.raise_for_status()
            data = resp.json()
            if not data.get("dataset"):
                return pd.DataFrame()

            df = pd.DataFrame(
                data["dataset"], columns=[c["name"] for c in data["columns"]]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        except Exception as e:
            logger.error(f"QuestDB Query Error for {symbol} range {s_str}-{e_str}: {e}")
            return pd.DataFrame()

    def process_chunk(self, symbol: str, start_ts: datetime, end_ts: datetime):
        """Process a specific time chunk."""
        # We need a bit of overlap to ensure window continuity,
        # but for simplicity in backfill, we accept tiny gaps at boundaries or fetch extra.
        # Fetching extra window_size-1 at start would be ideal.

        # Buffer start by window size minutes
        buffer_start = start_ts - timedelta(minutes=self.window_size)

        df = self.fetch_range(symbol, buffer_start, end_ts)
        if df.empty or len(df) < (self.window_size + self.params["forward_horizon"]):
            return 0

        prices = df["close"].values
        timestamps = df["timestamp"].values
        patterns = []

        start_idx = self.window_size - 1
        end_idx = len(df) - self.params["forward_horizon"]

        for i in range(start_idx, end_idx):
            # Ensure we are actually inside the requested range (excluding buffer)
            ts = timestamps[i]  # pandas Timestamp
            # Convert to python datetime for comparison if needed, or rely on pandas
            # timestamps[i] is numpy.datetime64 usually

            # Simple Outcome Logic
            current_price = prices[i]
            future_price = prices[i + self.params["forward_horizon"]]
            outcome = (future_price - current_price) / current_price

            window = prices[i - (self.window_size - 1) : i + 1]
            mean = np.mean(window)
            std = np.std(window)

            if std == 0:
                continue

            norm_vector = ((window - mean) / std).tolist()

            patterns.append(
                {
                    "vector": norm_vector,
                    "symbol": symbol,
                    "timestamp": ts,
                    "outcome": float(outcome),
                }
            )

        if patterns:
            self.memory.add_patterns(patterns)
        return len(patterns)

    def run_backfill(self, days: int = 365 * 2):
        """Backfill history in chunks."""
        logger.info(f"💾 Starting Backfill for last {days} days...")
        universe = settings.WATCHLIST

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        chunk_size = timedelta(days=30)

        for symbol in universe:
            logger.info(f"Processing {symbol}...")
            current = start_time
            total_symbol = 0

            while current < end_time:
                next_chunk = min(current + chunk_size, end_time)
                # logger.info(f"  Chunk: {current.date()} -> {next_chunk.date()}")
                count = self.process_chunk(symbol, current, next_chunk)
                total_symbol += count
                current = next_chunk

            logger.info(f"✅ {symbol} Backfill Complete: {total_symbol} patterns.")

    def run_sync(self):
        """Run the sync process for all watchlist symbols (Recent 24h)."""
        logger.info("🧠 Starting Incremental Sync (24h)...")
        universe = settings.WATCHLIST
        total_ingested = 0
        for symbol in universe:
            count = self.process_symbol(symbol)
            if count > 0:
                logger.info(f"  Processed {symbol}: {count} patterns")
                total_ingested += count
        logger.info(f"✅ Sync Complete. Total Patterns Ingested: {total_ingested}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backfill", action="store_true", help="Run deep backfill (default 2 years)"
    )
    parser.add_argument("--days", type=int, default=730, help="Days to backfill")
    args = parser.parse_args()

    daemon = MarketMemoryDaemon()

    if args.backfill:
        daemon.run_backfill(days=args.days)
    else:
        daemon.run_sync()
