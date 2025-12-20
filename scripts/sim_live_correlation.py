import asyncio
import os
import logging
import csv
import signal
import sys
from datetime import datetime, timedelta
from collections import deque
from typing import Optional

# Third-party Imports
from alpaca.data.live.crypto import CryptoDataStream
from alpaca.data.live.stock import StockDataStream

# Internal Imports
from app.services.physics import PhysicsService
from app.agent.nodes.analyst import (
    AnalystAgent,
)  # Used for warmup helper if needed, or just direct Physics

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("CC_LiveSim")

# Constants
SYMBOL = "SPY"
STREAM_TYPE = "STOCK"  # 'CRYPTO' or 'STOCK'
CSV_FILE = "data/sim_results_spy.csv"
LOOKBACK_MINUTES = 5


class LiveSimulator:
    def __init__(self):
        self.running = True
        self.physics = PhysicsService()
        self.history_buffer = deque(
            maxlen=LOOKBACK_MINUTES + 1
        )  # Store (time, price) tuples
        self.crashes = 0

        # Ensure data directory exists
        os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)

        # Init CSV if not exists
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Timestamp",
                        "Price",
                        "Velocity",
                        "Acceleration",
                        "Alpha",
                        "Regime",
                        "Return_5m_Pct",
                    ]
                )

    def _flush_to_csv(self, row: list):
        """Append a row to CSV and flush immediately."""
        try:
            with open(CSV_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(row)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
        except Exception as e:
            logger.error(f"Failed to write to CSV: {e}")

    async def warmup(self):
        """Warm up the Physics Engine with historical data."""
        logger.info("🔥 Warming up Physics Engine...")
        try:
            # We can use AnalystAgent's market service to get valid warmup data
            # Or just use the PhysicsService if we had a direct data source.
            # Instantiating AnalystAgent just for market access is heavy but reliable.
            analyst = AnalystAgent()
            # Use Alpaca for 1-minute warmup bars
            from alpaca.data.historical import CryptoHistoricalDataClient
            from alpaca.data.requests import CryptoBarsRequest
            from alpaca.data.timeframe import TimeFrame
            import os

            api_key = os.getenv("ALPACA_API_KEY")
            secret_key = os.getenv("ALPACA_API_SECRET")

            bars = []
            if api_key and secret_key:
                client = CryptoHistoricalDataClient(api_key, secret_key)
                for sym in [SYMBOL, SYMBOL.replace("/", "")]:  # Try BTC/USD then BTCUSD
                    try:
                        req = CryptoBarsRequest(
                            symbol_or_symbols=[sym],
                            timeframe=TimeFrame.Minute,
                            limit=100,
                        )
                        bars_response = await asyncio.to_thread(
                            client.get_crypto_bars, req
                        )
                        if sym in bars_response:
                            bars = [b.close for b in bars_response[sym]]
                            if bars:
                                logger.info(
                                    f"✅ Warmup data fetched using symbol: {sym}"
                                )
                                break
                    except Exception as e:
                        logger.warning(f"Failed to fetch history for {sym}: {e}")

            if not bars:
                logger.warning(
                    "⚠️ No intraday warmup data found. Trying daily history fallback..."
                )
                bars = await asyncio.to_thread(
                    analyst.market.get_startup_bars, SYMBOL, 100
                )

            if bars:
                # PhysicsService expects a list of floats
                self.physics.calculate_kinematics(prices=bars)
                logger.info(
                    f"✅ Physics Warmed Up. Initial Velocity: {self.physics.kf.x[1]:.5f}"
                )
            else:
                logger.warning(
                    "⚠️ No warmup data available. Physics starting from scratch (cold)."
                )

        except Exception as e:
            logger.error(f"Warmup failed: {e}")
            logger.warning("⚠️ Proceeding with cold start.")

    async def handle_bar(self, bar):
        """Process a single bar from the stream."""
        try:
            timestamp = datetime.now()
            # Handle Alpaca Bar object (it has .close, .high, etc)
            price = float(bar.close)

            # 1. Update Physics
            kinematics = self.physics.calculate_kinematics(new_price=price)
            regime_data = self.physics.analyze_regime(self.physics.price_history_buffer)

            velocity = kinematics.get("velocity", 0.0)
            acceleration = kinematics.get("acceleration", 0.0)
            alpha = regime_data.get("alpha", 3.0)
            regime = regime_data.get("regime", "Gaussian")

            # 2. Update buffer for Return Calculation
            self.history_buffer.append((timestamp, price))

            # 3. Calculate 5m Return
            return_5m_pct = 0.0
            if len(self.history_buffer) > LOOKBACK_MINUTES:
                # The oldest item is T-5 (since maxlen is Lookback + 1, index 0 is T-5)
                # Actually maxlen=6 (0..5). Index 0 is T-5, Index -1 is Current.
                past_time, past_price = self.history_buffer[0]
                if past_price > 0:
                    return_5m_pct = ((price - past_price) / past_price) * 100

            # 4. Log to Disk
            row = [
                timestamp.isoformat(),
                price,
                velocity,
                acceleration,
                alpha,
                regime,
                f"{return_5m_pct:.4f}",
            ]
            self._flush_to_csv(row)

            # 5. Update HUD
            # "⏱️ {time} | 💲 {price} | 🚀 Vel: {v} | 🛑 Alpha: {alpha} | 🔮 5m-Return: {ret}%"
            time_str = timestamp.strftime("%H:%M:%S")
            vel_icon = "🚀" if velocity > 0 else "🔻"
            alpha_icon = (
                "🟢" if alpha > 1.7 else "🛑"
            )  # Stop if Alpha is low (Critical)

            print(
                f"⏱️ {time_str} | 💲 {price:,.2f} | {vel_icon} Vel: {velocity:+.5f} | {alpha_icon} Alpha: {alpha:.2f} | 🔮 5m-Return: {return_5m_pct:+.2f}%"
            )

        except Exception as e:
            import traceback

            logger.error(f"Error processing bar: {e}")
            traceback.print_exc()

    async def run(self):
        """Main loop with auto-reconnect."""
        await self.warmup()

        api_key = os.environ.get("ALPACA_API_KEY")
        secret_key = os.environ.get("ALPACA_API_SECRET")

        if not api_key or not secret_key:
            logger.critical(
                "❌ Missing ALPACA_API_KEY or ALPACA_API_SECRET in environment."
            )
            return

        logger.info(f"📡 Connecting to Alpaca {STREAM_TYPE} Stream for {SYMBOL}...")

        while self.running:
            try:
                if STREAM_TYPE == "CRYPTO":
                    stream = CryptoDataStream(api_key, secret_key)
                else:
                    stream = StockDataStream(api_key, secret_key)

                # Subscribe
                stream.subscribe_bars(self.handle_bar, SYMBOL)

                # Run Forever (until error)
                await stream._run_forever()

            except Exception as e:
                self.crashes += 1
                logger.error(
                    f"🚨 Stream Disconnected: {e}. Reconnecting in 5s... (Crash #{self.crashes})"
                )
                await asyncio.sleep(5)
            except KeyboardInterrupt:
                logger.info("🛑 User stopped simulation.")
                self.running = False
                break


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    sim = LiveSimulator()

    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        sim.running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        asyncio.run(sim.run())
    except KeyboardInterrupt:
        pass
