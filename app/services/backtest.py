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
import orjson
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from tqdm import tqdm
from redis.asyncio import Redis

from app.core.config import settings
from app.services.forecast import TimeSeriesForecaster
from app.dal.backtest import BacktestDAL

# Logger
logger = logging.getLogger("BacktestEngine")
logging.basicConfig(level=logging.INFO)


class BacktestEngine:
    """
    The Quantum Holodeck.

    A vectorized simulation engine that allows "The Council" to re-live history.
    It simulates:
    1. Time Travel (Historical Re-play via QuestDB)
    2. Parallel Universes (Vectorized independent symbol tracking)
    3. Counterfactual Outcomes (What if?)

    Unlike event-driven backtesters, this engine prioritizes speed over tick-precision.
    It is designed to validate "The Oracle's" prophecies at scale.
    """

    def __init__(self, start_date: str, end_date: str, run_id: Optional[str] = None):
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.run_id = run_id

        # 1. Initialize Oracle (Unified Forecaster)
        logger.info("🧠 Initializing Oracle for Simulation...")
        self.forecaster = TimeSeriesForecaster()

        # 2. Portfolio State
        self.portfolio = {
            "cash": 100000.0,
            "positions": {},  # {symbol: quantity}
            "equity_curve": [],
            "history": [],
            "trades": [],
        }

        # 3. Data Cache
        self.market_data: Dict[str, pd.DataFrame] = {}

        # 4. Persistence & Streaming
        self.dal = BacktestDAL()
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = Redis.from_url(self.redis_url, decode_responses=False)

    def load_data(self):
        """
        Load all Tier 1 data from QuestDB into memory.
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
        total_steps = len(timeline)
        logger.info(f"🎬 Starting Simulation: {total_steps} steps.")

        # Context window size
        CTX_LEN = 64

        try:
            for step_idx, t in enumerate(tqdm(timeline)):
                # 1. Prepare Batch
                current_prices = {}
                context_batch = []
                symbols_in_batch = []

                for symbol, df in self.market_data.items():
                    if t in df.index:
                        # Get price at t
                        price = float(df.loc[t]["close"])
                        current_prices[symbol] = price

                        history_slice = df.loc[:t].iloc[-CTX_LEN:]

                        if len(history_slice) == CTX_LEN:
                            # Vectors
                            ctx_vals = history_slice["close"].values.astype(np.float32)
                            context_batch.append(ctx_vals)
                            symbols_in_batch.append(symbol)

                if not context_batch:
                    continue

                # Convert to Tensor
                batch_tensor = torch.tensor(
                    np.array(context_batch), dtype=torch.float32
                )

                # --- Batch Prediction (The Holodeck) ---
                # Returns List[Dict] with 'q_values', 'q_labels', 'trend'
                batch_results = await self.forecaster.predict_batch(batch_tensor)

                # --- Iterate Results (Execution) ---
                for i, symbol in enumerate(symbols_in_batch):
                    res = batch_results[i]
                    trend = res.get("trend", 0.0)

                    # Decile Arrays
                    # [q05, q15, q25, q35, q50, q65, q75, q85, q95]
                    q_vals = res.get("q_values", [])

                    if len(q_vals) < 9:
                        # Fallback / Error
                        continue

                    q05 = q_vals[0]
                    q50 = q_vals[4]
                    q95 = q_vals[8]
                    price = current_prices[symbol]

                    # --- Skew & Vol Metrics ---
                    # Vol Width = (q95 - q05) / Price
                    vol_width = (q95 - q05) / price if price > 0 else 0.0

                    # Skew Ratio = (q95 - q50) / (q50 - q05)
                    # > 1.0 (Right Skew / Upside)
                    # < 1.0 (Left Skew / Crash Risk)
                    lower_span = q50 - q05
                    skew_ratio = 1.0
                    if lower_span > 0.000001:
                        skew_ratio = (q95 - q50) / lower_span

                    # Basic Signal Logic
                    signal = "NEUTRAL"
                    confidence = 0.0

                    # "Oracle Strategy": Follow Trend
                    if abs(trend) > 0.0005:  # 5bps threshold
                        signal = "BUY" if trend > 0 else "SELL"
                        # Simple Confidence based on vol_width? (Narrower = Better?)
                        # Or just fixed high confidence
                        confidence = 0.8

                    # 3. Execution (Sim)
                    self._execute(
                        symbol,
                        signal,
                        confidence,
                        price,
                        t,
                        vol_width=vol_width,
                        skew_ratio=skew_ratio,
                    )

                # Update Equity Curve & Stream
                await self._update_equity(t, step_idx, total_steps)

            # Final Report
            report = await self._report()

            # Persist to QuestDB
            if self.run_id and report:
                await self.dal.log_completion(self.run_id, report)
                # Stream Completion
                await self.redis.publish(
                    f"backtest:{self.run_id}",
                    orjson.dumps({"type": "COMPLETED", "metrics": report}),
                )

        except Exception as e:
            logger.error(f"Backtest Failed: {e}", exc_info=True)
            if self.run_id:
                await self.redis.publish(
                    f"backtest:{self.run_id}",
                    orjson.dumps({"type": "FAILED", "error": str(e)}),
                )
        finally:
            await self.redis.close()

    def _execute(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        price: float,
        t: datetime,
        vol_width: float = 0.0,
        skew_ratio: float = 1.0,
    ):
        """
        Simulate Execution with Asymmetric Risk & Predatory Slippage.

        1. Sizing: Base on Vol Width, adjusted by Skew.
        2. Slippage: Predatory based on Vol Width.
        """
        # Confidence Filter (The Gate)
        if confidence < 0.6:
            return

        qty = 0
        current_pos = self.portfolio["positions"].get(symbol, 0)

        # Base Allocation
        TARGET_ALLOC = 10000.0

        if signal == "BUY":
            if current_pos <= 0:
                cost_needed = TARGET_ALLOC

                # --- 1. SKEW-ADJUSTED SIZING ---
                # A. Volatility Sizing (Inverse to Width)
                # Base logic: If width is small (Calm), size up?
                # Request says: Base Size = 1.0 / vol_width
                # This implies aggressive size for low vol.
                # We normalize against a "Baseline Width" to generate a scalar.
                # Let's say Baseline Width is 1% (0.01).
                # If vol_width is 0.05, factor is 0.2.
                # If vol_width is 0.005, factor is 2.0.

                # Careful with "Infinite" size. Cap it.
                BASE_WIDTH = 0.01
                if vol_width > 0:
                    vol_factor = BASE_WIDTH / vol_width
                else:
                    vol_factor = 1.0

                # Cap Vol Factor at 2.0 (2x Leverage max) and Floor at 0.1
                vol_factor = max(0.1, min(2.0, vol_factor))

                cost_needed *= vol_factor

                # B. Skew Adjustment
                # < 0.8 (Crash Risk) -> 0.5x
                # > 1.5 (Melt-up) -> 1.2x
                if skew_ratio < 0.8:
                    cost_needed *= 0.5
                elif skew_ratio > 1.5:
                    cost_needed *= 1.2

                # Check Cash
                if self.portfolio["cash"] > cost_needed:
                    qty_to_buy = cost_needed / price
                    if current_pos < 0:
                        qty = abs(current_pos) + qty_to_buy
                    else:
                        qty = qty_to_buy

        elif signal == "SELL":
            if current_pos > 0:
                qty = -current_pos  # Close All

        if qty != 0:
            # --- 2. PREDATORY SLIPPAGE ---
            # slippage = 0.0002 * (1 + (implied_vol * 10))
            # implied_vol = vol_width

            base_slip = 0.0002
            # E.g. Vol Width 0.05 -> 1 + 0.5 = 1.5x -> 0.0003 (3bps)
            # E.g. Vol Width 0.20 -> 1 + 2.0 = 3.0x -> 0.0006 (6bps)
            slippage_pct = base_slip * (1.0 + (vol_width * 10.0))

            # Cap at 5%
            slippage_pct = min(slippage_pct, 0.05)

            slippage_amt = price * slippage_pct

            # Buy High, Sell Low
            exec_price = price + slippage_amt if qty > 0 else price - slippage_amt
            fee = abs(qty) * 0.005  # $0.005 per share

            cost_basis = abs(qty) * exec_price

            if qty > 0:
                self.portfolio["cash"] -= cost_basis + fee
            else:
                self.portfolio["cash"] += cost_basis - fee

            self.portfolio["positions"][symbol] = current_pos + qty

            # Log Trade
            self.portfolio["trades"].append(
                {
                    "symbol": symbol,
                    "timestamp": t,
                    "side": signal,
                    "qty": qty,
                    "price": exec_price,
                    "slippage": slippage_amt,
                    "vol_width": vol_width,
                    "skew": skew_ratio,
                    "fee": fee,
                }
            )

    async def _update_equity(self, t: datetime, step: int, total: int):
        val = self.portfolio["cash"]
        for sym, qty in self.portfolio["positions"].items():
            if qty != 0:
                # Need current price.
                if t in self.market_data[sym].index:
                    price = self.market_data[sym].loc[t]["close"]
                    val += qty * price

        # Calculate Drawdown
        current_eq = val
        self.portfolio["history"].append(current_eq)
        peak = max(self.portfolio["history"])
        drawdown = (current_eq / peak - 1) if peak > 0 else 0

        self.portfolio["equity_curve"].append(
            {"timestamp": t, "equity": current_eq, "drawdown": drawdown}
        )

        # Stream Progress to Dragonfly
        if self.run_id and step % 10 == 0:
            packet = {
                "type": "progress",
                "progress": round(step / total, 4),
                "equity": round(current_eq, 2),
                "timestamp": t.isoformat(),
            }
            await self.redis.publish(f"backtest:{self.run_id}", orjson.dumps(packet))

    async def _report(self):
        eq = pd.DataFrame(self.portfolio["equity_curve"])
        if eq.empty:
            logger.info("No trades.")
            return {"metrics": {}, "equity": [], "trades": []}

        eq.set_index("timestamp", inplace=True)
        ret = eq["equity"].pct_change().dropna()

        start_eq = 100000.0  # Assumed initial
        end_eq = eq["equity"].iloc[-1]

        total_ret = (end_eq - start_eq) / start_eq
        sharpe = ret.mean() / ret.std() * np.sqrt(252 * 390) if ret.std() > 0 else 0
        max_dd = (eq["equity"] / eq["equity"].cummax() - 1).min()

        logger.info("=" * 30)
        logger.info(" BACKTEST REPORT")
        logger.info("=" * 30)
        logger.info(f"Return: {total_ret:.2%}")
        logger.info(f"Sharpe: {sharpe:.2f}")
        logger.info(f"Max DD: {max_dd:.2%}")
        logger.info("=" * 30)

        # Log Logic: Call QuestDB async log_equity_curve
        if self.run_id:
            await self.dal.log_equity_curve(self.run_id, self.portfolio["equity_curve"])

        return {
            "metrics": {
                "total_return": total_ret,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "final_equity": end_eq,
            },
            "equity": self.portfolio["equity_curve"],
            "trades": self.portfolio["trades"],
        }


if __name__ == "__main__":
    # Example Run
    engine = BacktestEngine("2023-11-01", "2023-11-05")
    engine.load_data()
    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        pass
