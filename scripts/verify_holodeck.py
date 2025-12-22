import asyncio
import logging
import torch
import numpy as np
import pandas as pd
from datetime import datetime
from app.services.backtest import BacktestEngine
from app.services.forecast import TimeSeriesForecaster
import sys

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - HOLODECK - %(levelname)s - %(message)s"
)
logger = logging.getLogger("HolodeckVerify")


async def verify_holodeck():
    print("\n🔮 Initiating Holodeck Verification Protocol (Phase 35.2)...")

    # 1. Mock Data Setup
    engine = BacktestEngine("2023-01-01", "2023-01-02")

    # Symbols for two scenarios
    # CALM: Low Vol Width
    # STORM: High Vol Width
    symbols = ["CALM", "STORM"]
    dates = pd.date_range("2023-01-01", periods=200, freq="1min", tz="UTC")

    print(f"📊 Injecting Mock Data...")

    for sym in symbols:
        np.random.seed(42)
        price_ret = np.random.normal(0, 0.001, len(dates))
        prices = 100 * np.cumprod(1 + price_ret)
        df = pd.DataFrame({"close": prices}, index=dates)
        engine.market_data[sym] = df

    # 2. Mock Forecaster Logic
    # We want to force specific vol_widths to test sizing

    original_predict = engine.forecaster.predict_batch

    async def mock_predict(tensor):
        batch_size = tensor.shape[0]
        results = []

        # We need to assume the order of tensor matches symbols logic or random
        # Since we can't easily map tensor row to symbol name here without context,
        # we will alternate the results.
        # CALM will get low width, STORM will get high width.
        # However, verifying which row corresponds to which symbol is tricky in batch only from tensor.
        # But `run` loop builds batch by iterating symbols dictionary order? No, iteration order.
        # engine.market_data is dict.

        # Let's just output alternating result and we will check the trades.

        for i in range(batch_size):
            # Alternating Logic
            if i % 2 == 0:
                # SCENARIO A: CALM (Low Width)
                # Vol Width 2% -> Spread 2.0 on 100.0
                # Skew Neutral: q05=99, q50=100, q95=101
                q_vals = [99.0, 99.2, 99.5, 99.8, 100.0, 100.2, 100.5, 100.8, 101.0]
                vol_width = 0.02
                trend = 0.01  # BUY
            else:
                # SCENARIO B: STORM (High Width)
                # Vol Width 10% -> Spread 10.0 on 100.0
                # Skew Neutral: q05=95, q50=100, q95=105
                q_vals = [95.0, 96.0, 97.5, 98.5, 100.0, 101.5, 102.5, 104.0, 105.0]
                vol_width = 0.10
                trend = 0.01  # BUY

            res = {
                "q_values": q_vals,
                "q_labels": [0.05, 0.15, 0.25, 0.35, 0.50, 0.65, 0.75, 0.85, 0.95],
                "trend": trend,
                # Legacy keys optional
            }
            results.append(res)

        return results

    # Inject Mock
    engine.forecaster.predict_batch = mock_predict
    print("✅ Injected Mock Predictor with Alternating Volatility Regimes.")

    # 3. Run Engine
    print("\n🚀 Engaging Hyperdrives...")
    await engine.run()

    # 4. Analyze Results
    trades = engine.portfolio["trades"]
    if not trades:
        print("❌ No trades executed.")
        sys.exit(1)

    print(f"\n✅ {len(trades)} Trades Executed.")

    # Separate trades by symbol (assuming CALM and STORM were processed)
    # Since we alternated in mock, and dict order might vary, we look at the implied sizing consequences.

    # Inspect Trades
    # Symbol names might map to the alternating logic depending on iteration order.
    # Python 3.7+ dicts preserve insertion order.
    # symbols = ["CALM", "STORM"] inserted in order.
    # So "CALM" should be index 0 (Even) -> Low Vol -> Full Size
    # "STORM" should be index 1 (Odd) -> High Vol -> Half Size

    calm_trades = [t for t in trades if t["symbol"] == "CALM"]
    storm_trades = [t for t in trades if t["symbol"] == "STORM"]

    if not calm_trades or not storm_trades:
        print("⚠️ Warning: Missing trades for one symbol.")

    # Check Average Quantity
    avg_qty_calm = np.mean([abs(t["qty"]) for t in calm_trades])
    avg_qty_storm = np.mean([abs(t["qty"]) for t in storm_trades])

    print(f"🌊 CALM Avg Qty:  {avg_qty_calm:.2f} (Expected ~100 with price 100)")
    print(f"🌪️ STORM Avg Qty: {avg_qty_storm:.2f} (Expected ~50 with price 100)")

    ratio = avg_qty_storm / avg_qty_calm
    print(f"⚖️  Scaling Ratio: {ratio:.2f}")

    # Assert Scaling
    # STORM width 10% vs CALM 2% -> 5x Volatility -> ~0.2x Scaling (Inverse Sizing)
    # Expected Ratio: 0.20
    if 0.15 < ratio < 0.35:
        print(
            "✅ Fractal Sizing Confirmed: Position Aggressively Reduced in High Volatility."
        )
    else:
        print(
            f"❌ Fractal Sizing FAILED. Ratio {ratio:.2f} outside expected range 0.15-0.35."
        )
        sys.exit(1)

    print("\n✅ High-Resolution Quantum State Verified.")


if __name__ == "__main__":
    try:
        asyncio.run(verify_holodeck())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Verification Failed: {e}", exc_info=True)
        sys.exit(1)
