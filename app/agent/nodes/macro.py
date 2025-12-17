"""
Parallel Macro Scanner Node.
Implements the "Quantum Field Scanner" using ThreadPoolExecutor and Pandas.
"""

from app.agent.state import AgentState
import logging
from typing import Dict, Any
from opentelemetry import trace
from app.services.market import MarketService
import pandas as pd
import concurrent.futures
import time

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# HARDCODED UNIVERSE (High Liquidity, "Power Law" Candidates)
UNIVERSE = [
    "SPY",
    "QQQ",
    "IWM",  # Indices
    "NVDA",
    "TSLA",
    "AMD",
    "MSFT",
    "AAPL",
    "GOOGL",
    "AMZN",
    "META",  # Big Tech
    "TQQQ",
    "SQQQ",
    "SOXL",  # Leveraged ETFs
    "COIN",
    "MSTR",  # Crypto Proxies
    "GME",  # Meme Legacy
    "GLD",
    "USO",  # Commodities
]


@tracer.start_as_current_span("node_macro_scanner_parallel")
def macro_node(state: AgentState) -> Dict[str, Any]:
    """
    Parallel Macro Scanner Node.
    Mission: Hunt for Volatility (The "Energy" of the market).

    Architecture:
    1. Parallel Fetch (ThreadPoolExecutor): Get snapshots for all N symbols concurrently.
    2. Vectorized Filtering (Pandas): Filter by Price > 10, Vol > 1M instantly.
    3. Energy Calculation: Momentum Mass = Abs(Ret) * Active Volume.
    4. Tunneling & Superposition: Select Top Candidate BUT return Batch for future nodes.
    """
    start_time = time.time()
    logger.info(f"🌍 MACRO: Starting Parallel Scan for {len(UNIVERSE)} assets...")

    service = MarketService()

    # --- Step 1: Parallel Fetch ---
    snapshots = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Create a future for each symbol
        future_to_symbol = {
            executor.submit(service.get_market_snapshot, symbol): symbol
            for symbol in UNIVERSE
        }

        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                data = future.result()
                # Basic validation
                if data and "price" in data:
                    snapshots[symbol] = data
            except Exception as e:
                logger.warning(f"MACRO: Failed to fetch {symbol}: {e}")

    fetch_time = (time.time() - start_time) * 1000
    logger.info(f"MACRO: Fetched {len(snapshots)} snapshots in {fetch_time:.0f}ms")

    if not snapshots:
        logger.error("MACRO: CRITICAL FAILURE. No data fetched.")
        return {"market_data": {"symbol": "SPY"}, "candidates": []}

    # --- Step 2: DataFrame Construction ---
    rows = []
    for sym, data in snapshots.items():
        price = data.get("price", 0.0)
        history = data.get("history", [])

        # Calculate Physics Metrics (Bollinger & Volatility) for WKB
        upper_bb = price * 1.05  # Default if no history
        volatility = price * 0.01

        if len(history) >= 20:
            series = pd.Series(history)
            # Use last 20 bars
            window = series.iloc[-20:]
            mean = window.mean()
            std = window.std()
            upper_bb = mean + (2 * std)
            volatility = std  # Use Std Dev as "Kinetic Energy" / Volatility proxy

        rows.append(
            {
                "symbol": sym,
                "price": price,
                "volume": data.get("volume", 0),
                "open": data.get("open", 0.0),
                "upper_bb": upper_bb,
                "volatility": volatility,
            }
        )

    df = pd.DataFrame(rows)

    # --- Step 3: Vectorized Analysis (Pandas) ---
    try:
        # Filters
        MIN_VOL = 10_000_000  # $10M Volume
        MIN_PRICE = 5.0

        # Calculate Returns
        df["pct_change"] = 0.0
        mask_open_pos = df["open"] > 0
        df.loc[mask_open_pos, "pct_change"] = (
            df.loc[mask_open_pos, "price"] - df.loc[mask_open_pos, "open"]
        ) / df.loc[mask_open_pos, "open"]

        # Momentum Energy (Classical)
        df["energy"] = df["pct_change"].abs() * df["volume"]

        # Filter
        liquid_df = df[(df["price"] >= MIN_PRICE) & (df["volume"] >= MIN_VOL)].copy()

        if liquid_df.empty:
            logger.warning(
                "MACRO: No assets passed liquidity filter. Using raw DF sorted by vol."
            )
            # Fallback to top volume
            liquid_df = df.sort_values("volume", ascending=False).head(5)

        # --- PARALLEL PHYSICS: Calculate Hurst Exponent ---
        # We calculate H for all liquid candidates to find Signal Potential
        from app.lib.memory import FractalMemory

        # Helper for parallel execution
        def calc_hurst_safe(row):
            sym = row["symbol"]
            hist = snapshots[sym].get("history", [])
            if len(hist) < 30:
                return 0.5
            try:
                return FractalMemory.calculate_hurst(hist)
            except Exception:
                return 0.5

        # Execute in ThreadPool
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # liquid_df is a DataFrame, iterate rows
            # We map the function to the list of rows (dicts) or just iterate indices
            # Turning DF to records for map might be cleaner or just loop
            records = liquid_df.to_dict("records")
            hurst_results = list(executor.map(calc_hurst_safe, records))

        liquid_df["hurst"] = hurst_results

        # --- QUANTUM SCORING: Signal Potential ---
        # Signal Potential = |H - 0.5|
        # We value H=0.8 (Trend) same as H=0.2 (Reversion).
        # We dislike H=0.5 (Random).

        liquid_df["signal_potential"] = (liquid_df["hurst"] - 0.5).abs()

        # Sort by Signal Potential Descending
        ranked_df = liquid_df.sort_values("signal_potential", ascending=False)

        # Top 5 Watchlist
        watchlist_df = ranked_df.head(5)
        watchlist = watchlist_df.to_dict(orient="records")

        # Winner is the #1 Signal Potential
        winner_row = watchlist[0] if watchlist else {}
        winner_symbol = winner_row.get("symbol", "SPY")

        logger.info(
            f"MACRO: 🏆 Winner {winner_symbol} | H: {winner_row.get('hurst', 0.5):.2f} | "
            f"Pot: {winner_row.get('signal_potential', 0):.2f}"
        )

        return {
            "symbol": winner_symbol,
            "watchlist": watchlist,  # Pass the list of high-potential assets
            "candidates": watchlist,  # Backwards compatibility
            "status": "active",
        }

    except Exception as e:
        logger.exception(f"MACRO: DataFrame Vectorization Failed: {e}")
        return {"symbol": "SPY", "watchlist": [], "candidates": []}
