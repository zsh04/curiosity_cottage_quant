import asyncio
import os
import logging
import orjson
from datetime import datetime
from redis.asyncio import Redis
from app.services.state_stream import get_state_broadcaster

logger = logging.getLogger("watchtower")


class RedisBridge:
    """
    The Watchtower Bridge.
    Listens to Redis channels and pipes transformed data to the StateBroadcaster (Websockets).
    """

    _instance = None

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.running = False
        self.redis = None
        self.pubsub = None

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    async def start(self):
        if self.running:
            return

        logger.info("👁️ Watchtower Bridge: Connecting to Redis...")
        self.redis = Redis.from_url(self.redis_url, decode_responses=False)
        self.pubsub = self.redis.pubsub()

        # Subscribe to The Trinity
        await self.pubsub.subscribe(
            "physics.forces",
            "forecast.signals",
            "strategy.signals",
            # "market.tick.*" # Wildcard if needed, but psub needed
        )
        # For patterns:
        await self.pubsub.psubscribe("market.tick.*")

        self.running = True
        logger.info("👁️ Watchtower Bridge: Online. Watching the flows.")

        # Start the loop
        asyncio.create_task(self._loop())

    async def _loop(self):
        broadcaster = get_state_broadcaster()

        try:
            while self.running:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message:
                    await self._process_message(message, broadcaster)
                else:
                    await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Watchtower Failed: {e}")
            self.running = False

    async def _process_message(self, message, broadcaster):
        channel = (
            message["channel"].decode()
            if isinstance(message["channel"], bytes)
            else message["channel"]
        )
        data_bytes = message["data"]

        try:
            payload = orjson.loads(data_bytes)
            ui_packet = {}

            # 1. Physics -> Market Data
            if "physics.forces" in channel:
                # payload is ForceVector dict
                ui_packet["market"] = {
                    "symbol": payload.get("symbol", "UNKNOWN"),
                    "price": payload.get("price", 0.0),
                    "alpha": payload.get("alpha_coefficient", 0.0),
                    "velocity": payload.get("momentum", 0.0),
                    "acceleration": payload.get("mass", 0.0),  # Loose mapping
                    "regime": self._derive_regime(
                        payload.get("alpha_coefficient", 2.0)
                    ),
                    "history": [],  # Dashboard handles history accumulation usually, or we assume separate history stream
                }

            # 2. Chronos -> Forecast
            elif "forecast.signals" in channel:
                # payload is ForecastPacket
                # Dashboard expects arrays?? ForecastData: {median: [], p10: [], p90: []}
                # But ForecastPacket has scalar p50? No, let's check model.
                # Actually Chronos model creates scalars (p10, p50, p90) for T+Horizon.
                # Dashboard seems to expect arrays for a curve?
                # Let's map scalar to single point array for now, or check Chronos service again.
                # ChronosService emits p10, p50, p90 as floats.
                # We will send arrays of length 1 or match Dashboard expectation.
                ui_packet["forecast"] = {
                    "median": [payload.get("p50", 0.0)],
                    "p10": [payload.get("p10", 0.0)],
                    "p90": [payload.get("p90", 0.0)],
                }

            # 3. Soros -> Signal
            elif "strategy.signals" in channel:
                # payload is TradeSignal
                meta = payload.get("meta", {})
                ui_packet["signal"] = {
                    "side": payload.get("side", "HOLD"),
                    "confidence": payload.get("strength", 0.0),
                    "score": payload.get("strength", 0.0),
                    "strategy": "SOROS_TRINITY",
                    "reasoning": str(meta),  # Flatten meta to string
                }
                # Also extract sentiment if available
                ui_packet["sentiment"] = {
                    "label": "Bullish"
                    if payload.get("side") == "BUY"
                    else ("Bearish" if payload.get("side") == "SELL" else "Neutral"),
                    "score": 0.5
                    + (
                        0.5
                        * payload.get("strength", 0.0)
                        * (1 if payload.get("side") == "BUY" else -1)
                    ),
                }

            # Broadcast if we have data
            if ui_packet:
                header = {
                    "timestamp": datetime.now().isoformat(),
                    "source": "watchtower",
                    **ui_packet,
                }
                await broadcaster.broadcast(header)

        except Exception as e:
            logger.warning(f"Watchtower Parse Error: {e}")

    def _derive_regime(self, alpha):
        if alpha > 2.0:
            return "GAUSSIAN (Safe)"
        if alpha > 1.5:
            return "LÉVY STABLE (Risky)"
        return "CRITICAL (Chaos)"
