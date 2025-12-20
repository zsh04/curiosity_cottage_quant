import os
import logging
import orjson
from datetime import datetime
from faststream import FastStream
from faststream.redis import RedisBroker
from app.core.models import ForceVector, TradeSignal, Side

# Configure The Philosopher
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | SOROS | %(levelname)s | %(message)s"
)
logger = logging.getLogger("soros")

# Initialize The Nervous System
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
broker = RedisBroker(redis_url)
app = FastStream(broker)


class SorosService:
    """
    The Soros Agent (Reflexivity Engine).

    "Markets are always wrong in the sense that they operate with a prevailing bias."

    Role: Transforms Physics Forces -> Trade Signals.
    Philosophy: Predatory. Vetoes Randomness. Exploits Reflexivity (Momentum + Nash).
    """

    def apply_reflexivity(self, force: ForceVector) -> TradeSignal:
        """
        The Logic Core.
        Applies strict filtering gates to find truth in the noise.
        """
        reasoning = {}

        # --- Gate 1: The Alpha Veto (Fat Tails) ---
        # If Alpha <= 2.0, the market is effectively Gaussian or worse (Lévy Stable),
        # meaning infinite variance is possible (or simply not tailored enough).
        # We demand Alpha > 2.0 (Finite Variance, Exploitable).
        if force.alpha_coefficient <= 2.0:
            reasoning["veto"] = "ALPHA_TOO_LOW"
            reasoning["alpha"] = force.alpha_coefficient
            return self._create_signal(
                force.symbol, Side.HOLD, 0.0, force.price, reasoning
            )

        # --- Gate 2: The Chaos Veto (Entropy) ---
        # If Entropy > 0.8, the system is too disordered. Information content is low.
        if force.entropy > 0.8:
            reasoning["veto"] = "CHAOS_DETECTED"
            reasoning["entropy"] = force.entropy
            return self._create_signal(
                force.symbol, Side.HOLD, 0.0, force.price, reasoning
            )

        # --- Gate 3: Reflexivity (Momentum + Nash) ---
        # We look for Clean Trends where:
        # 1. Momentum supports the move.
        # 2. Price is NOT too far extended (Nash Distance within limits),
        #    OR perhaps we want it NOT overextended?
        #    Prompt Spec:
        #    - Mom > 0 AND Nash < 2.0 -> BUY (Trend is up, not yet overbought)
        #    - Mom < 0 AND Nash > -2.0 -> SELL (Trend is down, not yet oversold)

        side = Side.HOLD
        strength = 0.0

        if force.momentum > 0 and force.nash_dist < 2.0:
            side = Side.BUY
            strength = 1.0  # Maximum aggression for now
            reasoning["thesis"] = "CLEAN_UP_TREND"

        elif force.momentum < 0 and force.nash_dist > -2.0:
            side = Side.SELL
            strength = 1.0
            reasoning["thesis"] = "CLEAN_DOWN_TREND"

        else:
            reasoning["veto"] = "OVEREXTENDED_OR_MEAN_REVERSION"
            reasoning["nash"] = force.nash_dist
            reasoning["momentum"] = force.momentum

        # Log significant triggers
        if side != Side.HOLD:
            logger.info(
                f"Reflexivity Triggered: {side.value} {force.symbol} (Strength {strength}) | {reasoning}"
            )

        return self._create_signal(force.symbol, side, strength, force.price, reasoning)

    def _create_signal(
        self, symbol: str, side: Side, strength: float, price: float, meta: dict
    ) -> TradeSignal:
        return TradeSignal(
            timestamp=datetime.now(),
            symbol=symbol,
            side=side,
            strength=strength,
            price=price,
            meta=meta,
        )


# Instantiate
soros = SorosService()


@broker.subscriber("physics.forces")
async def handle_physics(msg: bytes):
    """
    Consumes physics vectors.
    Applies Reflexivity.
    Publishes Signals.
    """
    try:
        # Decode and Validate Input
        data = orjson.loads(msg)
        # Handle cases where input might be dict or list (though physics sends dict)
        # Or if serialized with Pydantic .model_dump_json(), it's a dict.
        # If 'vectors' key exists (from Feynman wrapper), extract it?
        # Feynman sent: {"symbol":..., "vectors": {...}}
        # But ForceVector expects flat structure?
        # Let's check Feynman output structure.
        # Feynman: packet = {"symbol": symbol, "timestamp": data.get("timestamp"), "vectors": forces}
        # Forces dict: {mass, momentum...}
        # ForceVector Model expects: timestamp, symbol, mass, momentum...

        # We need to flatten/map the input to ForceVector
        vectors = data.get("vectors", {})
        payload = {
            "timestamp": datetime.fromtimestamp(data.get("timestamp", 0) / 1000.0)
            if isinstance(data.get("timestamp"), (int, float))
            else datetime.now(),
            "symbol": data.get("symbol"),
            **vectors,
        }

        force = ForceVector(**payload)

        # Think
        signal = soros.apply_reflexivity(force)

        # Act
        await broker.publish(signal.model_dump_json(), channel="strategy.signals")

    except Exception as e:
        logger.error(f"Reflexivity Failed: {e}", exc_info=True)
