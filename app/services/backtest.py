"""
The Holodeck: High-Performance Vectorized Backtesting Engine.

Simulates the Unified Forecasting Engine in a strictly causal loop.
Identity: The Simulation Architect.
"""

import asyncio
import logging
import pandas as pd
import numpy as np
import torch
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from app.core.config import settings
from app.services.forecast import TimeSeriesForecaster
from app.services.rag_forecast import MarketMemory

# Logger
logger = logging.getLogger("BacktestEngine")
logging.basicConfig(level=logging.INFO)


class BacktestEngine:
    """
    The Quantum Holodeck.
    Runs the Unified Forecaster on historical data with strict causality.
    """

    def __init__(self, start_date: str, end_date: str):
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)

        # 1. Initialize Oracle (Unified Forecaster)
        logger.info("🧠 Initializing Oracle for Simulation...")
        self.forecaster = TimeSeriesForecaster()

        # 2. Portfolio State
        self.portfolio = {
            "cash": 100000.0,
            "positions": {},  # {symbol: quantity}
            "equity_curve": [],
            "history": [],
        }

        # 3. Data Cache
        self.market_data: Dict[str, pd.DataFrame] = {}

    def load_data(self):
        """
        Load all Tier 1 data from QuestDB into memory.
        Pre-calculates contexts? Or fetch on fly?
        For speed, we want to preload the entire range for all symbols.
        """
        universe = settings.WATCHLIST
        logger.info(f"💾 Loading Data for {len(universe)} symbols...")

        # We need a bit of buffer BEFORE start_date for context (64 bars)
        buffer_start = self.start_date - pd.Timedelta(hours=4)  # ample buffer

        start_str = buffer_start.strftime("%Y-%m-%dT%H:%M:%S.000000Z")
        end_str = self.end_date.strftime("%Y-%m-%dT%H:%M:%S.000000Z")

        for symbol in universe:
            query = f"""
            SELECT timestamp, close 
            FROM 'ohlcv_1min' 
            WHERE symbol = '{symbol}' 
            AND timestamp >= '{start_str}' AND timestamp <= '{end_str}'
            ORDER BY timestamp ASC
            """
            try:
                resp = requests.get(
                    f"{settings.QUESTDB_URL}/exec", params={"query": query}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("dataset"):
                        df = pd.DataFrame(
                            data["dataset"],
                            columns=[c["name"] for c in data["columns"]],
                        )
                        df["timestamp"] = pd.to_datetime(df["timestamp"])
                        df.set_index("timestamp", inplace=True)
                        self.market_data[symbol] = df
                        logger.info(f"  loaded {symbol}: {len(df)} bars")
            except Exception as e:
                logger.error(f"Failed to load {symbol}: {e}")

        logger.info("✅ Data Loading Complete.")

    async def run(self):
        """
        The Time Loop.
        Iterate through time, batch predict, update usage.
        """
        if not self.market_data:
            logger.error("No data loaded. Aborting.")
            return

        # Create Timeline (Union of all timestamps in range)
        # FORCE UTC
        timeline = pd.date_range(
            start=self.start_date, end=self.end_date, freq="1min", tz="UTC"
        )
        logger.info(f"🎬 Starting Simulation: {len(timeline)} steps.")

        # Context window size
        CTX_LEN = 64

        # Debug counter
        matches_found = 0

        for t in tqdm(timeline):
            # 1. Prepare Batch
            current_prices = {}
            context_batch = []
            symbols_in_batch = []

            for symbol, df in self.market_data.items():
                if t in df.index:
                    matches_found += 1
                    # Get price at t
                    price = float(df.loc[t]["close"])
                    current_prices[symbol] = price

                    # Get context (previous 64 bars ending at t)
                    # Slicing: since index is sorted, we can slice.
                    # We need strictly the last 64 rows UP TO t.
                    # df.loc[:t] includes t.
                    # Optimization: slice by integer position if possible, but index lookup is safe.
                    history_slice = df.loc[:t].iloc[-CTX_LEN:]

                    if len(history_slice) == CTX_LEN:
                        # Vectors
                        ctx_vals = history_slice["close"].values.astype(np.float32)
                        context_batch.append(ctx_vals)
                        symbols_in_batch.append(symbol)

            if not context_batch:
                logger.debug(
                    f"No context batch for timestamp {t}. Skipping."
                )  # Added debug log
                continue

            # Convert to Tensor
            batch_tensor = torch.tensor(np.array(context_batch), dtype=torch.float32)

            # 2. Predict (Ensemble)
            # We treat the batch as a batch for Chronos?
            # Our current predict_ensemble takes 'current_prices' as a LIST.
            # But here we have multiple symbols.
            # The current TimeSeriesForecaster.predict_ensemble signature:
            # (context_tensor, current_prices: List[float]) -> Dict
            # It expects a single stream or batch?
            # Reviewing forecast.py:
            # predict_ensemble takes context_tensor (Batch x Time).
            # But 'current_prices' is used for RAF.
            # RAF logic: "if len(current_prices) >= window_size: recent_window = current_prices[-window:]"
            # This implies 'current_prices' is history for ONE symbol. Not a list of prices for the batch.

            # FIX: We need to loop per symbol for the Ensemble call roughly, OR update Forecaster to handle batch RAF.
            # Forecaster RAF logic is single-vector.
            # For Simulation MVP, we can iterate the batch or run sequentially.
            # Given we want "Vectorized Backtest", we should ideally vectorise RAF too.
            # But RAF search is per-vector.
            # Let's iterate for now. The Chronos part handles batching natively? current logic uses [0] index for result.

            # Temporary Loop for Simulation Safety
            for i, symbol in enumerate(symbols_in_batch):
                ctx = batch_tensor[i]  # (64,)
                raw_history = context_batch[i].tolist()  # List[float]

                # Predict
                packet = await self.forecaster.predict_ensemble(
                    ctx, raw_history, cutoff_timestamp=t
                )

                # Signal Processing
                signal = packet.get("signal", "NEUTRAL")  # BUY/SELL/NEUTRAL/FLAT
                conf = packet.get("confidence", 0.0)

                # 3. Execution (Sim)
                self._execute(symbol, signal, conf, current_prices[symbol], t)

            # Update Equity Curve
            self._update_equity(t)

        self._report()

    def _execute(
        self, symbol: str, signal: str, confidence: float, price: float, t: datetime
    ):
        """Simulate Execution with Slippage and Fees."""
        if confidence < 0.6:
            return  # Filter

        qty = 0
        if signal == "BUY":
            # Simple logic: Alloc 10k per trade
            amt = 10000
            if self.portfolio["cash"] > amt:
                qty = amt / price
        elif signal == "SELL":
            # For backtest, assume we can sell held positions or short.
            # Let's just close longs for now or flip.
            current_pos = self.portfolio["positions"].get(symbol, 0)
            if current_pos > 0:
                qty = -current_pos  # Close all

        if qty != 0:
            # Fees & Slippage
            slippage = price * 0.0002  # 2 bps
            exec_price = price + slippage if qty > 0 else price - slippage
            fee = abs(qty) * 0.005  # $0.005 per share

            cost = (abs(qty) * exec_price) + fee

            if qty > 0:
                self.portfolio["cash"] -= cost
            else:
                self.portfolio["cash"] += (abs(qty) * exec_price) - fee

            self.portfolio["positions"][symbol] = (
                self.portfolio["positions"].get(symbol, 0) + qty
            )

            # Log Trade
            # logger.info(f"x {t} {signal} {symbol} {qty:.2f} @ {exec_price:.2f}")

    def _update_equity(self, t: datetime):
        val = self.portfolio["cash"]
        for sym, qty in self.portfolio["positions"].items():
            if qty != 0:
                # Need current price.
                # Optimization: passed via arg or lookup
                # Taking from cache
                if t in self.market_data[sym].index:
                    price = self.market_data[sym].loc[t]["close"]
                    val += qty * price

        self.portfolio["equity_curve"].append({"timestamp": t, "equity": val})

    def _report(self):
        eq = pd.DataFrame(self.portfolio["equity_curve"])
        if eq.empty:
            logger.info("No trades.")
            return

        eq.set_index("timestamp", inplace=True)
        ret = eq["equity"].pct_change().dropna()

        total_ret = (eq["equity"].iloc[-1] - 100000) / 100000
        sharpe = ret.mean() / ret.std() * np.sqrt(252 * 390) if ret.std() > 0 else 0
        max_dd = (eq["equity"] / eq["equity"].cummax() - 1).min()

        logger.info("=" * 30)
        logger.info(" BACKTEST REPORT")
        logger.info("=" * 30)
        logger.info(f"Return: {total_ret:.2%}")
        logger.info(f"Sharpe: {sharpe:.2f}")
        logger.info(f"Max DD: {max_dd:.2%}")
        logger.info("=" * 30)


if __name__ == "__main__":
    # Example Run
    engine = BacktestEngine("2023-11-01", "2023-11-05")
    engine.load_data()
    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        pass
