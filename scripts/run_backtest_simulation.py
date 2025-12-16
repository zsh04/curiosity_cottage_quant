#!/usr/bin/env python3
"""
Backtest Simulation Runner for CC-V2 Autonomous Trading System

This script runs a comprehensive backtest of the multi-modal trading agent:
1. Fetches historical market data from TimescaleDB
2. Simulates agent decision-making with realistic latency
3. Models market microstructure (slippage, spread, commissions)
4. Calculates performance metrics (Sharpe, Max Drawdown, Total Return)
5. Generates equity curve visualization vs SPY benchmark

Requirements:
- TimescaleDB with historical MarketTick data
- 3+ months of SPY data
- Analyst Agent (LLM can be mocked for speed)

Usage:
    python scripts/run_backtest_simulation.py
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Force IPv4 for local connection to avoid "role postgres does not exist" on localhost ipv6
os.environ["DATABASE_URL"] = "postgresql://postgres:password@127.0.0.1:5432/quant_db"
# Dummy credentials to allow MarketAdapter to initialize (methods will be mocked)
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "PKTEST1234567890")
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET", "dummy_secret_value")

# Set them in os.environ for components that might directly read from it
os.environ["ALPACA_API_KEY"] = ALPACA_API_KEY
os.environ["ALPACA_API_SECRET"] = ALPACA_API_SECRET

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.dal.database import get_db
from app.dal.models import MarketTick
from app.backtest.engine import BacktestEngine
from app.backtest.execution import SimulatedExecutionHandler, RealisticExecution
from app.backtest.portfolio import Portfolio
from app.backtest.feed import HistoricalCSVDataFeed
from app.backtest.strategy_wrapper import (
    AnalystStrategy,
)  # UPGRADED: Real Physics Agent


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================
# Configuration
# ============================================


class BacktestConfig:
    """Backtest configuration parameters"""

    # Capital
    INITIAL_CAPITAL = 100_000.0

    # Agent Latency (seconds) - UPGRADED for real AnalystAgent
    AGENT_LATENCY_MS = 2000  # 2 seconds (LLM + Chronos + Kalman)

    # Market Microstructure
    SPREAD_BPS = 5.0  # 5 basis points
    COMMISSION_PER_SHARE = 0.005  # $0.005/share (Alpaca tier)
    MIN_COMMISSION = 1.0  # $1 minimum
    MARKET_IMPACT_FACTOR = 0.1

    # Execution Latency
    EXECUTION_LATENCY_MS = 100  # 100ms to fill

    # Data Range - REDUCED to 1 month for faster testing
    SYMBOL = "SPY"
    LOOKBACK_MONTHS = 1  # 1 month for initial test

    # Agent Configuration
    USE_MOCK_LLM = True  # True = Fast (velocity heuristic), False = Real (Ollama)
    USE_MOCK_SENTIMENT = False  # False = Real (FinBERT)

    # Output
    OUTPUT_DIR = Path("backtest_results")
    PLOT_EQUITY_CURVE = True


# ============================================
# Data Loading from TimescaleDB
# ============================================


def fetch_market_data_from_db(
    symbol: str, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    """
    Fetch historical market tick data from TimescaleDB.

    Args:
        symbol: Asset symbol (e.g., 'SPY')
        start_date: Start of backtest period
        end_date: End of backtest period

    Returns:
        DataFrame with OHLCV data indexed by timestamp
    """
    logger.info(f"📊 Fetching {symbol} data from {start_date} to {end_date}...")

    db: Session = next(get_db())

    try:
        # Query market ticks
        ticks = (
            db.query(MarketTick)
            .filter(
                MarketTick.symbol == symbol,
                MarketTick.time >= start_date,
                MarketTick.time <= end_date,
            )
            .order_by(MarketTick.time)
            .all()
        )

        if not ticks:
            logger.error(f"❌ No data found for {symbol} in the specified range")
            return pd.DataFrame()

        # Convert to DataFrame
        data = []
        for tick in ticks:
            data.append(
                {
                    "timestamp": tick.time,
                    "open": tick.open,
                    "high": tick.high,
                    "low": tick.low,
                    "close": tick.close,
                    "volume": tick.volume,
                }
            )

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)

        logger.info(f"✅ Loaded {len(df)} bars for {symbol}")
        logger.info(f"   Date range: {df.index[0]} to {df.index[-1]}")
        logger.info(
            f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}"
        )

        return df

    finally:
        db.close()


# ============================================
# Performance Reporting
# ============================================


def calculate_performance_metrics(
    equity_curve: pd.Series, benchmark_curve: pd.Series
) -> dict:
    """
    Calculate comprehensive performance metrics.

    Args:
        equity_curve: Strategy equity over time
        benchmark_curve: Buy-and-hold benchmark

    Returns:
        Dictionary of performance metrics
    """
    logger.info("📈 Calculating performance metrics...")

    # Returns
    strategy_returns = equity_curve.pct_change().dropna()
    benchmark_returns = benchmark_curve.pct_change().dropna()

    # Total return
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1.0
    benchmark_total_return = (benchmark_curve.iloc[-1] / benchmark_curve.iloc[0]) - 1.0

    # Sharpe ratio (annualized, assuming daily bars)
    if len(strategy_returns) > 1 and strategy_returns.std() > 0:
        sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Maximum drawdown
    cumulative = (1 + strategy_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    # Benchmark max drawdown
    benchmark_cumulative = (1 + benchmark_returns).cumprod()
    benchmark_running_max = benchmark_cumulative.cummax()
    benchmark_drawdown = (
        benchmark_cumulative - benchmark_running_max
    ) / benchmark_running_max
    benchmark_max_drawdown = benchmark_drawdown.min()

    # Win rate
    winning_days = (strategy_returns > 0).sum()
    total_days = len(strategy_returns)
    win_rate = winning_days / total_days if total_days > 0 else 0.0

    # Alpha (excess return vs benchmark)
    alpha = total_return - benchmark_total_return

    return {
        "total_return": float(total_return),
        "total_return_pct": float(total_return * 100),
        "benchmark_return": float(benchmark_total_return),
        "benchmark_return_pct": float(benchmark_total_return * 100),
        "alpha": float(alpha),
        "alpha_pct": float(alpha * 100),
        "sharpe_ratio": float(sharpe),
        "max_drawdown": float(max_drawdown),
        "max_drawdown_pct": float(max_drawdown * 100),
        "benchmark_max_drawdown_pct": float(benchmark_max_drawdown * 100),
        "win_rate": float(win_rate),
        "win_rate_pct": float(win_rate * 100),
        "total_days": int(total_days),
        "winning_days": int(winning_days),
    }


def plot_equity_curve(
    equity_curve: pd.Series,
    benchmark_curve: pd.Series,
    metrics: dict,
    output_path: Path,
):
    """
    Plot strategy equity curve vs benchmark.

    Args:
        equity_curve: Strategy equity over time
        benchmark_curve: Benchmark equity
        metrics: Performance metrics dictionary
        output_path: Where to save the plot
    """
    logger.info("📊 Generating equity curve plot...")

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [3, 1]}
    )

    # Plot 1: Equity curves
    ax1.plot(
        equity_curve.index,
        equity_curve.values,
        label="Strategy",
        linewidth=2,
        color="#2E86AB",
    )
    ax1.plot(
        benchmark_curve.index,
        benchmark_curve.values,
        label="SPY Buy-and-Hold",
        linewidth=2,
        linestyle="--",
        color="#A23B72",
        alpha=0.7,
    )

    ax1.set_title(
        f"CC-V2 Backtest: Strategy vs Benchmark\n"
        f"Period: {equity_curve.index[0].strftime('%Y-%m-%d')} to {equity_curve.index[-1].strftime('%Y-%m-%d')}",
        fontsize=14,
        fontweight="bold",
    )
    ax1.set_ylabel("Portfolio Value ($)", fontsize=12)
    ax1.legend(loc="best", fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(
        y=BacktestConfig.INITIAL_CAPITAL, color="gray", linestyle=":", alpha=0.5
    )

    # Format y-axis as currency
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

    # Plot 2: Drawdown
    strategy_returns = equity_curve.pct_change().dropna()
    cumulative = (1 + strategy_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max

    ax2.fill_between(drawdown.index, 0, drawdown.values * 100, alpha=0.3, color="red")
    ax2.plot(drawdown.index, drawdown.values * 100, color="darkred", linewidth=1)
    ax2.set_ylabel("Drawdown (%)", fontsize=12)
    ax2.set_xlabel("Date", fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.1f}%"))

    # Add metrics text box
    metrics_text = (
        f"Strategy Return: {metrics['total_return_pct']:.2f}%\n"
        f"Benchmark Return: {metrics['benchmark_return_pct']:.2f}%\n"
        f"Alpha: {metrics['alpha_pct']:.2f}%\n"
        f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n"
        f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%\n"
        f"Win Rate: {metrics['win_rate_pct']:.1f}%"
    )

    props = dict(boxstyle="round", facecolor="wheat", alpha=0.8)
    ax1.text(
        0.02,
        0.98,
        metrics_text,
        transform=ax1.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=props,
        family="monospace",
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    logger.info(f"✅ Plot saved to: {output_path}")

    # Also show if running interactively
    # plt.show()


# ============================================
# Main Backtest Runner
# ============================================


def run_backtest():
    """
    Main backtest execution function.
    """
    logger.info("=" * 70)
    logger.info("🚀 CC-V2 BACKTEST SIMULATION")
    logger.info("=" * 70)

    # Create output directory
    BacktestConfig.OUTPUT_DIR.mkdir(exist_ok=True)

    # Step 1: Define date range
    # Run for full 1 year (as data was seeded for 1 year)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    logger.info(f"\n📅 Backtest Period:")
    logger.info(f"   Start: {start_date.strftime('%Y-%m-%d')}")
    logger.info(f"   End:   {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"   Symbol: {BacktestConfig.SYMBOL}")
    logger.info(f"   Initial Capital: ${BacktestConfig.INITIAL_CAPITAL:,.2f}")

    # Step 2: Fetch Data
    df = fetch_market_data_from_db(BacktestConfig.SYMBOL, start_date, end_date)

    if df.empty:
        logger.error("❌ Aborting: No data loaded")
        return

    # Step 3: Initialize Backtest Components
    logger.info("\n⚙️  Initializing backtest components...")

    # Configure Adapters for Localhost (Running outside Docker)
    os.environ["CHRONOS_URL"] = "http://localhost:8002"
    os.environ["FINBERT_URL"] = "http://localhost:8001"
    os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
    os.environ["LLM_MODEL"] = "gemma2:9b"  # Ensure we use the model we pulled

    # Data feed
    data_feed = HistoricalCSVDataFeed({BacktestConfig.SYMBOL: df})

    # Portfolio
    portfolio = Portfolio(
        initial_capital=BacktestConfig.INITIAL_CAPITAL,
        start_date=start_date,
        data_feed=data_feed,
    )

    # Execution handler with realistic microstructure
    execution_model = RealisticExecution(
        spread_bps=BacktestConfig.SPREAD_BPS,
        commission_per_share=BacktestConfig.COMMISSION_PER_SHARE,
        min_commission=BacktestConfig.MIN_COMMISSION,
        impact_factor=BacktestConfig.MARKET_IMPACT_FACTOR,
    )

    execution_handler = SimulatedExecutionHandler(
        execution_model=execution_model,
        latency_ms=BacktestConfig.EXECUTION_LATENCY_MS,
        data_feed=data_feed,
    )

    # UPGRADED: Real AnalystAgent with Physics + Chronos + LLM
    logger.info("\\n🧠 Initializing AnalystAgent Strategy...")
    strategy = AnalystStrategy(
        mock_llm=BacktestConfig.USE_MOCK_LLM,
        mock_sentiment=BacktestConfig.USE_MOCK_SENTIMENT,
        lookback_bars=100,
    )

    if BacktestConfig.USE_MOCK_LLM:
        logger.info("   ⚡ LLM Mode: MOCK (velocity heuristic - FAST)")
    else:
        logger.info("   🐌 LLM Mode: REAL (Ollama Gemma2 - SLOW)")

    logger.info("   📊 Strategy: Multi-Modal Physics Agent")
    logger.info("      - Fractional Differentiation")
    logger.info("      - Kalman Filter (3-state)")
    logger.info("      - Chronos Forecast")
    logger.info("      - Sentiment Analysis (mocked)")
    logger.info(
        f"      - LLM Reasoning ({'mocked' if BacktestConfig.USE_MOCK_LLM else 'real'})"
    )

    # Backtest engine
    engine = BacktestEngine(
        data_feed=data_feed,
        portfolio=portfolio,
        execution_handler=execution_handler,
        strategy=strategy,
        agent_latency_ms=BacktestConfig.AGENT_LATENCY_MS,
    )

    logger.info("\\n📐 Backtest Parameters:")
    logger.info(f"   ✅ Agent Latency: {BacktestConfig.AGENT_LATENCY_MS}ms")
    logger.info(f"   ✅ Spread: {BacktestConfig.SPREAD_BPS}bps")
    logger.info(f"   ✅ Commission: ${BacktestConfig.COMMISSION_PER_SHARE}/share")
    logger.info(f"   ✅ Market Impact: {BacktestConfig.MARKET_IMPACT_FACTOR}")

    # Step 4: Run backtest
    logger.info(f"\n🎯 Running backtest...")
    engine.run()

    # Step 5: Extract results
    logger.info(f"\n📊 Extracting results...")

    # Portfolio equity curve
    history_df = pd.DataFrame(portfolio.history)
    if history_df.empty:
        logger.error("❌ No portfolio history generated")
        return

    history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
    history_df.set_index("timestamp", inplace=True)
    equity_curve = history_df["total_equity"]

    # Benchmark (SPY buy-and-hold)
    initial_shares = BacktestConfig.INITIAL_CAPITAL / df["close"].iloc[0]
    benchmark_curve = df["close"] * initial_shares
    benchmark_curve.name = "total_equity"

    # Align indices
    common_index = equity_curve.index.intersection(benchmark_curve.index)
    equity_curve = equity_curve.loc[common_index]
    benchmark_curve = benchmark_curve.loc[common_index]

    # Step 6: Calculate metrics
    metrics = calculate_performance_metrics(equity_curve, benchmark_curve)

    # Print results
    logger.info("\n" + "=" * 70)
    logger.info("📈 BACKTEST RESULTS")
    logger.info("=" * 70)
    logger.info(f"Strategy Total Return:    {metrics['total_return_pct']:>8.2f}%")
    logger.info(f"Benchmark Total Return:   {metrics['benchmark_return_pct']:>8.2f}%")
    logger.info(f"Alpha (Excess Return):    {metrics['alpha_pct']:>8.2f}%")
    logger.info(f"Sharpe Ratio:             {metrics['sharpe_ratio']:>8.2f}")
    logger.info(f"Max Drawdown:             {metrics['max_drawdown_pct']:>8.2f}%")
    logger.info(
        f"Benchmark Max Drawdown:   {metrics['benchmark_max_drawdown_pct']:>8.2f}%"
    )
    logger.info(f"Win Rate:                 {metrics['win_rate_pct']:>8.1f}%")
    logger.info(f"Trading Days:             {metrics['total_days']:>8d}")
    logger.info("=" * 70)

    # Execution summary
    exec_summary = execution_handler.get_execution_summary()
    logger.info(f"\n📋 EXECUTION SUMMARY")
    logger.info(f"   Total Fills:          {exec_summary['total_fills']}")
    logger.info(f"   Total Commission:     ${exec_summary['total_commission']:.2f}")
    logger.info(f"   Total Slippage:       ${exec_summary['total_slippage']:.2f}")
    logger.info(
        f"   Avg Commission/Fill:  ${exec_summary['avg_commission_per_fill']:.2f}"
    )

    # Step 7: Plot equity curve
    if BacktestConfig.PLOT_EQUITY_CURVE:
        plot_path = (
            BacktestConfig.OUTPUT_DIR
            / f"equity_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        plot_equity_curve(equity_curve, benchmark_curve, metrics, plot_path)

    # Save metrics to JSON
    import json

    metrics_path = (
        BacktestConfig.OUTPUT_DIR
        / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"\n✅ Metrics saved to: {metrics_path}")

    logger.info(f"\n✅ Backtest complete!")


if __name__ == "__main__":
    try:
        run_backtest()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Backtest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Backtest failed: {e}", exc_info=True)
        sys.exit(1)
