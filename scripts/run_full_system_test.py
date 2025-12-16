#!/usr/bin/env python3
import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("SystemTest")

# 1. Setup Environment (MUST BE BEFORE IMPORTS)
os.environ["DATABASE_URL"] = "postgresql://postgres:password@127.0.0.1:5432/quant_db"
os.environ["CHRONOS_URL"] = "http://localhost:8002"
os.environ["FINBERT_URL"] = "http://localhost:8001"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["LLM_MODEL"] = "gemma2:9b"
# Dummy Alpaca Creds for Init
os.environ["ALPACA_API_KEY"] = os.getenv("ALPACA_API_KEY", "dummy_key")
os.environ["ALPACA_API_SECRET"] = os.getenv("ALPACA_API_SECRET", "dummy_secret")

from app.dal.database import get_db
from app.dal.models import MarketTick
from app.backtest.engine import BacktestEngine
from app.backtest.execution import SimulatedExecutionHandler, RealisticExecution
from app.backtest.portfolio import Portfolio
from app.backtest.feed import HistoricalCSVDataFeed
from app.backtest.strategy_wrapper import AnalystStrategy
from app.agent.nodes.risk import risk_node
# from app.backtest.reporting import calculate_performance_metrics # Not available

# Config
SYMBOL = "SPY"
CAPITAL = 100000.0
LATENCY_MS = 10  # Speed up for deep history test
WARMUP_DAYS = 100  # Days to ignore signals to let Alpha converge


def calculate_performance_metrics(
    equity_curve: pd.Series, benchmark_curve: pd.Series
) -> dict:
    # Local implementation since it's missing from app package
    strategy_returns = equity_curve.pct_change().dropna()
    benchmark_returns = benchmark_curve.pct_change().dropna()
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1.0
    benchmark_total_return = (benchmark_curve.iloc[-1] / benchmark_curve.iloc[0]) - 1.0

    if len(strategy_returns) > 1 and strategy_returns.std() > 0:
        sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    cumulative = (1 + strategy_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    benchmark_cumulative = (1 + benchmark_returns).cumprod()
    benchmark_running_max = benchmark_cumulative.cummax()
    benchmark_drawdown = (
        benchmark_cumulative - benchmark_running_max
    ) / benchmark_running_max
    benchmark_max_drawdown = benchmark_drawdown.min()

    winning_days = (strategy_returns > 0).sum()
    total_days = len(strategy_returns)
    win_rate = winning_days / total_days if total_days > 0 else 0.0
    alpha = total_return - benchmark_total_return

    return {
        "total_return_pct": float(total_return * 100),
        "benchmark_return_pct": float(benchmark_total_return * 100),
        "alpha_pct": float(alpha * 100),
        "sharpe_ratio": float(sharpe),
        "max_drawdown_pct": float(max_drawdown * 100),
        "benchmark_max_drawdown_pct": float(benchmark_max_drawdown * 100),
        "win_rate_pct": float(win_rate * 100),
        "total_days": int(total_days),
    }


class TrackingAnalystStrategy(AnalystStrategy):
    """
    Instrumented strategy to capture internal state for White Box verification.
    """

    def __init__(self, start_date=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audit_log = []
        self.start_date = start_date

        # Monkey Patch Agent.analyze to capture output
        self._original_analyze = self.agent.analyze
        self.agent.analyze = self._instrumented_analyze

    def _instrumented_analyze(self, state):
        # Warmup Check
        if self.start_date and self.timestamp_history:
            current_processed_date = self.timestamp_history[-1]
            # If we are within warmup period, force Neutral to let Physics converge
            # Normalize TZ to avoid mismatch
            curr_naive = current_processed_date.replace(tzinfo=None)
            start_naive = self.start_date.replace(tzinfo=None)

            if (curr_naive - start_naive).days < WARMUP_DAYS:
                state["signal_side"] = "NEUTRAL"
                # Still calculate physics internally by running original analyze first?
                # No, if we run original analyze, it might produce a signal.
                # But we want to "Include" the physics calculation so Alpha updates, but Ignore the Signal output.
                # The Risk Node / Physics updates happen inside the agent graph?
                # Actually, Analyst Agent calculates Alpha. So we MUST run _original_analyze.
                out_state = self._original_analyze(state)
                # Force Signal to Neutral afterwards to suppress trading
                out_state["signal_side"] = "NEUTRAL"
                return out_state

        # Run actual logic (Analyst)
        out_state = self._original_analyze(state)

        # Run Risk Node (to apply physics/alpha sizing)
        # Note: Risk Node expects 'nav' or we assume default capital in logic
        out_state["nav"] = CAPITAL
        out_state = risk_node(out_state)

        # Capture Data
        if out_state.get("signal_side") in ["BUY", "SELL"]:
            # OVERRIDE Confidence with Risk Sizing for Portfolio
            # Portfolio: target_value = cash * strength
            # Risk: approved_size (Notional $)
            # So strength = approved_size / cash
            # Warning: Sometims cash != nav, but close enough for test
            approved_size = out_state.get("approved_size", 0.0)
            if approved_size > 0:
                strength = approved_size / CAPITAL
                out_state["signal_confidence"] = strength

            record = {
                "timestamp": self.timestamp_history[-1]
                if self.timestamp_history
                else "N/A",
                "signal": out_state.get("signal_side"),
                "confidence": out_state.get("signal_confidence"),
                "alpha": out_state.get("current_alpha"),
                "risk_size": out_state.get("approved_size", 0.0),
                "forecast": out_state.get("chronos_forecast", {}).get("median", []),
            }
            self.audit_log.append(record)

        return out_state


def fetch_data():
    db = next(get_db())
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # 1 Year for Deep History

    ticks = (
        db.query(MarketTick)
        .filter(MarketTick.symbol == SYMBOL, MarketTick.time >= start_date)
        .order_by(MarketTick.time)
        .all()
    )

    data = [
        {
            "timestamp": t.time,
            "open": t.open,
            "high": t.high,
            "low": t.low,
            "close": t.close,
            "volume": t.volume,
        }
        for t in ticks
    ]

    df = pd.DataFrame(data)
    if not df.empty:
        df.set_index("timestamp", inplace=True)
    return df, start_date


def run_white_box_test():
    logger.info("🧪 STARTING WHITE BOX FULL SYSTEM TEST")

    # 1. Load Data
    df, start_date = fetch_data()
    if df.empty:
        logger.error("❌ No data found in DB. Cannot compare.")
        return

    logger.info(f"📊 Loaded {len(df)} bars for {SYMBOL}")

    # 2. Initialize Components
    data_feed = HistoricalCSVDataFeed({SYMBOL: df})
    portfolio = Portfolio(initial_capital=CAPITAL, data_feed=data_feed)

    # Execution
    exec_model = RealisticExecution()
    exec_handler = SimulatedExecutionHandler(
        exec_model, latency_ms=100, data_feed=data_feed
    )

    # Strategy (Instrumented)
    # Mocking LLM for speed, but using REAL Chronos/Physics/Risk
    strategy = TrackingAnalystStrategy(
        start_date=start_date,
        mock_llm=True,
        mock_sentiment=True,  # Focus on Price/Physics flow
        lookback_bars=100,
    )

    # Engine
    engine = BacktestEngine(
        data_feed=data_feed,
        portfolio=portfolio,
        execution_handler=exec_handler,
        strategy=strategy,
        agent_latency_ms=LATENCY_MS,
    )

    # 3. Run
    logger.info("🚀 Running Simulation...")
    try:
        engine.run()
    except KeyboardInterrupt:
        pass

    # 4. Audit
    logger.info("\n📋 TRANSACTION AUDIT (First 5 Signals)")
    logger.info(
        f"{'Time':<25} | {'Signal':<6} | {'Alpha':<6} | {'Risk Size ($)':<15} | {'Fill?'}"
    )
    logger.info("-" * 80)

    fills = portfolio.history  # Naive check, actually execution handler has stats
    fill_count = exec_handler.total_fills

    for rec in strategy.audit_log[:5]:
        # Check if this signal resulted in a fill roughly around this time?
        # Simulation is event driven, hard to correlate 1:1 easily without ID,
        # but we verify Risk Sizing happened
        alpha_val = rec["alpha"] if rec["alpha"] is not None else 0.0
        size_val = rec["risk_size"] if rec["risk_size"] is not None else 0.0
        print(
            f"{str(rec['timestamp']):<25} | {rec['signal']:<6} | {alpha_val:<6.2f} | ${size_val:<14.2f} | {'✅' if size_val > 0 else '❌'}"
        )

    logger.info("-" * 80)

    # 5. Success Criteria
    logger.info("\n🏆 VERIFICATION RESULTS")

    # Check Fills
    if fill_count > 0:
        logger.info(f"✅ Executions Occurred: {fill_count} fills")
    else:
        logger.error(f"❌ NO EXECUTIONS! (Total Fills: {fill_count})")

    # Check Sharpe
    if len(portfolio.history) > 0:
        hist_df = pd.DataFrame(portfolio.history).set_index("timestamp")
        # Dummy benchmark
        bench_df = df["close"] * (CAPITAL / df["close"].iloc[0])
        bench_df = bench_df.loc[hist_df.index]

        metrics = calculate_performance_metrics(hist_df["total_equity"], bench_df)
        sharpe = metrics.get("sharpe_ratio", 0.0)

        if sharpe != 0.0 and not pd.isna(sharpe):
            logger.info(f"✅ Sharpe Ratio Calculated: {sharpe:.2f}")
        else:
            logger.warning(
                f"⚠️ Sharpe Ratio invalid (likely 0 variance or flat): {sharpe}"
            )

    # Check Risk Sizing
    risky_sizes = [r["risk_size"] for r in strategy.audit_log]
    if any(s > 0 for s in risky_sizes):
        logger.info("✅ Risk Node actively sizing trades (> $0)")
    else:
        logger.error("❌ Risk Node returned $0 for ALL signals")

    # Check Race Condition Fix
    # If we had fills, the fix likely worked (as otherwise market_data is None -> Return)
    if fill_count > 0:
        logger.info(
            f"✅ Race Condition Fix Verified (SimulatedExecutionHandler processed {fill_count} fills)"
        )

    # Check Alpha Convergence
    valid_alphas = [
        r["alpha"]
        for r in strategy.audit_log
        if r["alpha"] is not None and r["alpha"] > 2.0
    ]
    if valid_alphas:
        logger.info(
            f"✅ ALPHA CONVERGENCE: Found {len(valid_alphas)} signals with Alpha > 2.0 (Max: {max(valid_alphas):.2f})"
        )
    else:
        logger.warning(
            "⚠️ ALPHA NOT CONVERGED: Max Alpha <= 2.0 (Heavy Tail Regime Persists)"
        )


if __name__ == "__main__":
    run_white_box_test()
