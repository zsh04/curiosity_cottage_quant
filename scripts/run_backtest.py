"""
The Quantum Holodeck Runner.
CLI entry point for the Vectorized Backtest Engine.

Usage:
    python scripts/run_backtest.py --start 2023-01-01 --end 2023-06-01 --plot
"""

import argparse
import asyncio
import logging
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from app.services.backtest import BacktestEngine

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("HolodeckRunner")


async def main(args):
    logger.info(f"🚀 Initializing Quantum Holodeck ({args.start} -> {args.end})...")

    # Initialize Engine
    engine = BacktestEngine(start_date=args.start, end_date=args.end)

    # Load Data (Pre-computation)
    engine.load_data()

    # Run Simulation
    await engine.run()

    # Plotting
    if args.plot:
        equity_curve = engine.portfolio["equity_curve"]
        if not equity_curve:
            logger.warning("No equity curve to plot.")
            return

        df = pd.DataFrame(equity_curve)
        df.set_index("timestamp", inplace=True)

        plt.figure(figsize=(12, 6))
        plt.plot(df.index, df["equity"], label="Holodeck Strategy", color="#00ff00")
        plt.title(f"Backtest Equity Curve ({args.start} to {args.end})")
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value ($)")
        plt.grid(True, alpha=0.3)
        plt.legend()

        filename = "backtest_equity.png"
        plt.savefig(filename)
        logger.info(f"📈 Equity curve saved to {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The Quantum Holodeck Backtester")
    parser.add_argument(
        "--start", type=str, required=True, help="Start Date (YYYY-MM-DD)"
    )
    parser.add_argument("--end", type=str, required=True, help="End Date (YYYY-MM-DD)")
    parser.add_argument("--plot", action="store_true", help="Save equity curve plot")

    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        logger.info("🛑 Simulation Aborted by User.")
    except Exception as e:
        logger.error(f"💥 Simulation Failed: {e}")
