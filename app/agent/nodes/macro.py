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
        MIN_VOL = 500_000
        MIN_PRICE = 10.0

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
            liquid_df = df.sort_values("volume", ascending=False).head(3)

        # --- QUANTUM TUNNELING (WKB Approximation) ---
        # P_tunnel ~ exp( - sqrt( V - E ) )
        # Here: V = Upper BB, E = Price (Position).
        # Actually in QM, E is energy, V is potential.
        # If Price < UpperBB, we are "inside" the well.
        # Barrier width/height proxy: (UpperBB - Price).
        # Normalization factor: Volatility (The "Planck Constant" of the market?)

        # Gap = V - E
        liquid_df["barrier_gap"] = liquid_df["upper_bb"] - liquid_df["price"]

        # If Gap < 0 (Price > BB), Tunneling is 1.0 (Breakout)
        # If Gap > 0, P decays exponentially.
        # Formula: P = exp( - Gap / Volatility )
        # Using numpy implicitly via pandas/numpy arithmetic if available, or apply

        import numpy as np

        # Clip gap to min 0 for sqrt (or linear decay)
        # Using linear decay in exponent for simplicity: P = exp(-gap/vol)
        # Ideally: P = exp( - sqrt(gap) ) per WKB?
        # Let's use simple exponential decay as heuristic.
        # Add small epsilon to vol to avoid div/0

        liquid_df["tunnel_prob"] = np.where(
            liquid_df["barrier_gap"] <= 0,
            1.0,
            np.exp(-liquid_df["barrier_gap"] / (liquid_df["volatility"] + 1e-6)),
        )

        # Composite Score: Energy (Momentum) * TunnelProb (feasibility)
        liquid_df["quantum_score"] = liquid_df["energy"] * liquid_df["tunnel_prob"]

        # Sort by Quantum Score Descending
        ranked_df = liquid_df.sort_values("quantum_score", ascending=False)

        # --- Step 4: Selection (Tunneling) ---
        top_row = ranked_df.iloc[0]
        winner_symbol = top_row["symbol"]
        winner_change = top_row["pct_change"]

        logger.info(
            f"MACRO: 🏆 Winner {winner_symbol} | Change: {winner_change:.2%} | "
            f"TunnelP: {top_row['tunnel_prob']:.2f} | Score: {top_row['quantum_score']:.0f}"
        )

        # --- Step 5: Format Candidates (Superposition) ---
        # Convert top N back to list of dicts for the State
        top_candidates = ranked_df.head(5).to_dict(orient="records")

        # We need to ensure the Analyst has the FULL snapshot for the winner
        # In a true batch system, we'd pass all snapshots.
        # For now, we update 'market_data' for the primary flow, but attach 'candidates' for future batch nodes.

        return {
            "symbol": winner_symbol,
            "candidates": top_candidates,
            "status": "active",
        }

    except Exception as e:
        logger.exception(f"MACRO: DataFrame Vectorization Failed: {e}")
        return {"market_data": {"symbol": "SPY"}, "candidates": []}
