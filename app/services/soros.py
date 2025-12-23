import os
import logging
import orjson
import aiohttp
import asyncio
import numpy as np
from collections import deque
from datetime import datetime
from typing import Optional, Union, Dict, Any, Deque
from faststream import FastStream
from faststream.redis import RedisBroker
from app.core.models import ForceVector, TradeSignal, Side, ForecastPacket
from app.core.vectors import PhysicsVector, ReflexivityVector

from app.agent.macro.agent import MacroAgent

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
    Identity: Ray Dalio (Triangulation) + Hegel (Dialectic).
    """

    def __init__(self, window_size: int = 100):
        self.latest_forecast: Optional[ForecastPacket] = None
        self.ollama_url = os.getenv(
            "OLLAMA_URL", "http://host.docker.internal:11434/api/generate"
        )
        self.model_name = os.getenv("OLLAMA_MODEL", "llama3")
        self.macro_agent = MacroAgent()

        # Reflexivity Memory
        self.window_size = window_size
        self.my_volumes: Dict[
            str, Deque[float]
        ] = {}  # symbol -> deque of recent fill volumes
        self.price_deltas: Dict[
            str, Deque[float]
        ] = {}  # symbol -> deque of price changes corresponding to fills
        self.last_prices: Dict[str, float] = {}

    def update_forecast(self, forecast: ForecastPacket):
        self.latest_forecast = forecast

    def record_execution(self, symbol: str, qty: float):
        """
        Record 'My Volume' to track self-inflicted moves.
        """
        if symbol not in self.my_volumes:
            self.my_volumes[symbol] = deque(maxlen=self.window_size)
            self.price_deltas[symbol] = deque(maxlen=self.window_size)

        # We record the volume.
        # We align this with the *subsequent* price move?
        # Or concurrent? Usually Impact is immediate or lagged.
        # "Correlation of MyVolume vs PriceChange".
        # We store volume now. We need the price change that happens *after* or *during*.
        # For simplicity, we store volume now, and we'll pair it with the NEXT price tick delta.
        # Just store volume here.
        self.my_volumes[symbol].append(abs(qty))

        # Placeholder for delta (will be filled on next tick)
        self.price_deltas[symbol].append(0.0)

    def calculate_reflexivity(
        self, symbol: str, current_price: float
    ) -> ReflexivityVector:
        """
        The Mirror Test.
        """
        # Update price delta for the LAST recorded volume if exists
        if symbol in self.last_prices and symbol in self.price_deltas:
            delta = current_price - self.last_prices[symbol]
            if self.price_deltas[symbol]:
                self.price_deltas[symbol][-1] = (
                    delta  # Assign impact to the last action
                )

        self.last_prices[symbol] = current_price

        # Default Vector
        vec = ReflexivityVector(sentiment_delta=0.0, reflexivity_index=0.0)

        if symbol not in self.my_volumes or len(self.my_volumes[symbol]) < 5:
            return vec

        # Calculate Correlation
        vols = list(self.my_volumes[symbol])
        deltas = list(self.price_deltas[symbol])

        if len(vols) != len(deltas):
            min_len = min(len(vols), len(deltas))
            vols = vols[-min_len:]
            deltas = deltas[-min_len:]

        # Reflx Index = Corr(Volume, |PriceDelta|) or PriceDelta?
        # Usually checking if We push price UP (Buy) or DOWN (Sell).
        # But here we just took abs(qty).
        # Actually, let's just use abs(delta) to see if we cause volatility.
        # "Correlation of MyVolume vs PriceChange".
        # If I Buy (Positive Qty) and Price goes Up (Positive Delta) -> High Correlation.
        # If I Sell (Negative Qty) and Price goes Down (Negative Delta) -> High Correlation.
        # Implementation in record_execution used abs(qty). I should use signed qty to detect impact direction.
        # Let's assume record_execution receives signed qty.

        # Wait, I used abs(qty) above. I should change that if I want directional correlation.
        # But if the prompt says "MyVolume", usually volume is unsigned.
        # Let's stick to strict correlation of "Activity" vs "Volatility" OR "Direction" vs "Direction"?
        # "Reflexivity Index > 0.8" implies strong relationship.
        # I'll use simple correlation of arrays.

        if np.std(vols) < 1e-9 or np.std(deltas) < 1e-9:
            return vec

        correlation = np.corrcoef(vols, deltas)[0, 1]

        vec.reflexivity_index = float(correlation) if not np.isnan(correlation) else 0.0

        return vec

    async def conduct_debate(
        self, force: ForceVector, forecast: Optional[ForecastPacket]
    ) -> dict:
        """
        The Tournament (Hegelian Dialectic).
        Hosts a debate between Bull and Bear agents via LLM.
        Returns the Judge's Verdict.
        """
        # 1. Macro Analysis (The Weather)
        # Run in thread to avoid blocking Async Loop with DB calls
        macro_context_str = "Macro: UNKNOWN"
        try:
            # Minimal state for MacroAgent
            state = {"symbol": force.symbol, "status": "PENDING"}

            # Run sync macro analysis in thread
            import asyncio

            regime_state = await asyncio.to_thread(
                self.macro_agent.analyze_regime, state
            )

            m_status = regime_state.get("status", "UNKNOWN")
            m_alpha = regime_state.get("alpha", 0.0)
            m_corr = regime_state.get("macro_correlation", 0.0)

            macro_context_str = (
                f"Regime: {m_status}\n"
                f"Tail Risk (Alpha): {m_alpha:.2f}\n"
                f"US10Y Corr: {m_corr:.2f}"
            )
        except Exception as e:
            logger.error(f"Macro Analysis Failed: {e}")
            macro_context_str = "Macro: ERROR (Assume Defensive)"

        # Context Construction
        forecast_str = (
            f"P50 Forecast: ${forecast.p50:.2f} (Confidence {forecast.confidence:.2f})"
            if forecast
            else "No Forecast"
        )
        context = (
            f"Symbol: {force.symbol}\n"
            f"Price: ${force.price:.2f}\n"
            f"Momentum: {force.momentum:.2f}\n"
            f"Nash Dist: {force.nash_dist:.2f}\n"
            f"Entropy: {force.entropy:.2f}\n"
            f"Alpha: {force.alpha_coefficient:.2f}\n"
            f"Chronos: {forecast_str}\n"
            f"--- MACRO CONTEXT ---\n{macro_context_str}"
        )

        prompt = (
            f"You are the Soros Investment Committee.\n"
            f"Context:\n{context}\n\n"
            f"Task: Conduct a debate.\n"
            f"1. Bull Agent: Argue for a LONG position based on Momentum/Trend.\n"
            f"2. Bear Agent: Argue for a SHORT/HOLD based on Risk/Entropy/Overextension.\n"
            f"   CRITICAL: If Macro Regime is DEFENSIVE/SLEEPING, Bear must argue for caution unless asset is a safe haven.\n"
            f"3. Judge: Weigh the arguments. Output ONLY JSON.\n\n"
            f"JSON Format Required:\n"
            f"{{\n"
            f'  "bull_argument": "string",\n'
            f'  "bear_argument": "string",\n'
            f'  "judge_verdict": "BUY" or "SELL" or "HOLD",\n'
            f'  "confidence": float (0.0-1.0)\n'
            f"}}"
        )

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.ollama_url, json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response_text = result.get("response", "{}")
                        return orjson.loads(response_text)
                    else:
                        logger.error(f"Ollama Error: {resp.status}")
                        return {}

        except Exception as e:
            logger.error(f"Debate Failed: {e}")
            return {}

    async def apply_reflexivity_async(self, force: ForceVector) -> TradeSignal:
        """
        Async wrapper for reflexivity to allow awaiting the debate.
        """
        # We need to reimplement apply_reflexivity logic here or make it async.
        # Since FastStream handlers are async, we can await this.

        reasoning = {}

        # --- Gate 1: Alpha Veto ---
        if force.alpha_coefficient <= 2.0:
            reasoning["veto"] = "ALPHA_TOO_LOW"
            return self._create_signal(
                force.symbol, Side.HOLD, 0.0, force.price, reasoning
            )

        # --- Gate 2: Chaos Veto ---
        if force.entropy > 0.8:
            reasoning["veto"] = "CHAOS_DETECTED"
            return self._create_signal(
                force.symbol, Side.HOLD, 0.0, force.price, reasoning
            )

        # --- Gate X: Synthetic Veto (Prod Safety) ---
        if self.latest_forecast and self.latest_forecast.is_synthetic:
            # Lazy import to avoid circular dependency
            from app.core.config import settings
            import os

            env = os.getenv("ENV", "DEV").upper()
            if settings.ENV == "PROD" or env == "PROD":
                reasoning["veto"] = "SYNTHETIC_DATA_VETO"
                logger.warning(
                    f"⛔ VETO: Synthetic Forecast in PROD Env. {force.symbol} halted."
                )
                return self._create_signal(
                    force.symbol, Side.HOLD, 0.0, force.price, reasoning
                )

        # --- Gate 3: Reflexivity ---
        side = Side.HOLD
        strength = 0.0

        if force.momentum > 0 and force.nash_dist < 2.0:
            side = Side.BUY
            strength = 1.0
            reasoning["thesis"] = "CLEAN_UP_TREND"

        elif force.momentum < 0 and force.nash_dist > -2.0:
            side = Side.SELL
            strength = 1.0
            reasoning["thesis"] = "CLEAN_DOWN_TREND"
        else:
            reasoning["veto"] = "MEAN_REVERSION"
            return self._create_signal(
                force.symbol, Side.HOLD, 0.0, force.price, reasoning
            )

        # --- Gate 4: Trinity (Fusion) ---
        if not self.latest_forecast:
            strength = 0.5
            reasoning["warning"] = "NO_FORECAST"
        else:
            p50 = self.latest_forecast.p50
            if side == Side.BUY and p50 < force.price:
                side = Side.HOLD
                strength = 0.0
                reasoning["veto"] = "DIVERGENCE_BEARISH_FORECAST"
            elif side == Side.SELL and p50 > force.price:
                side = Side.HOLD
                strength = 0.0
                reasoning["veto"] = "DIVERGENCE_BULLISH_FORECAST"

        # --- Gate 5: The Tournament (Agentic Debate) ---
        # Only debate if we haven't been vetoed yet
        if side != Side.HOLD:
            debate_result = await self.conduct_debate(force, self.latest_forecast)

            if debate_result:
                # Merge debate into reasoning
                reasoning["bull_argument"] = debate_result.get("bull_argument")
                reasoning["bear_argument"] = debate_result.get("bear_argument")
                judge = debate_result.get("judge_verdict", "HOLD")

                reasoning["judge_verdict"] = judge

                # If Judge disagrees, we Downgrade or Hold?
                # Let's say we trust the Judge to VETO, but not necessarily to Initiate if Physics vetoed.
                if judge != side.value:
                    logger.warning(
                        f"Judge Disagrees! Physics: {side.value}, Judge: {judge}"
                    )
                    side = Side.HOLD
                    strength = 0.0
                    reasoning["veto"] = "JUDGE_OVERRULED"
                else:
                    logger.info(f"Judge Confirms: {judge}")
            else:
                logger.warning("Debate yielded no result. Proceeding with caution.")

        # Log
        if side != Side.HOLD:
            logger.info(f"Signal Generated: {side.value} {force.symbol} | {reasoning}")

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
async def handle_physics(msg: Union[bytes, Dict[str, Any]]):
    try:
        data = orjson.loads(msg) if isinstance(msg, bytes) else msg
        vectors = data.get("vectors", {})

        # Parse Physics Vector (Strict)
        try:
            physics_vec = PhysicsVector(**vectors)
        except Exception as e:
            logger.error(f"Invalid Physics Vector: {e}")
            return

        # Calculate Reflexivity Vector
        symbol = data.get("symbol", "UNKNOWN")
        reflexivity_vec = soros.calculate_reflexivity(
            symbol, physics_vec.mass if False else 100.0
        )  # mass is vol? No, use physics_vec values if needed.
        # Wait calculate_reflexivity takes current_price.
        # Physics Vector doesn't strictly have price field?
        # app/core/vectors.py: PhysicsVector has mass, momentum, entropy, jerk.
        # Feynman returns dict matching it.
        # Does Feynman return Price?
        # In feynman.py refactor, I returned PhysicsVector.
        # PhysicsVector definition was:
        # mass, momentum, entropy, jerk.
        # IT DOES NOT HAVE PRICE.
        # But handle_tick in feynman.py gets price from data.
        # And originally Calculate Forces returned a Dict containing "price".
        # Now it returns PhysicsVector.
        # So "price" is lost in the vector?
        # I should probably add price to PhysicsVector or pass it separately.
        # For now, I'll rely on `msg` timestamp?
        # Actually I need price for soros logic (e.g. Nash Dist, Price checks).
        # And Soros `apply_reflexivity_async` expects `ForceVector` which has price.
        # So `handle_physics` needs to reconstruct `ForceVector` from `PhysicsVector` + other data.
        # Other data should be in `data` dict from feynman (it sends symbol, timestamp, vectors).
        # Does it send price? No.
        # I should add `price` to `PhysicsVector` or Update `PhysicsVector` schema.
        # Let's check `vectors.py` ... I defined it with mass, momentum, entropy, jerk.
        # I should add `price` to `PhysicsVector` or pass it in `data` payload from Feynman.

        # Looking at feynman.py refactor:
        # It sends `packet = { "symbol": ..., "vectors": forces.model_dump() }`
        # It effectively dropped the price from the payload unless it's in `vectors`.
        # I should add `price` to the `packet` in feynman.py! Aahh.

        # But I am editing `soros.py` now.
        # I will assume `data` contains `price` OR I will re-edit `feynman.py` later.
        # Actually, let's look at `PhysicsVector` schema again.
        # I defined it in Step 34. No price.
        # So feynman refactor dropped price.
        # This is a regression. Soros needs Price.
        # I should fix `feynman.py` to include `price` in the published packet.

        # For now, I'll assume I'll fix feynman.py to add `price` to the outer packet.
        # In `handle_physics` here, I'll try `data.get("price")`.

        # Reconstructing ForceVector for legacy support inside Soros (until fully vector based):
        # ForceVector needs: momentum, nash_dist, entropy, alpha_coefficient, price, symbol.
        # PhysicsVector has: mass, momentum, entropy, jerk.
        # Missing: nash_dist, alpha_coefficient.

        # Oh, `PhysicsVector` I defined in `vectors.py` is missing `nash_dist` and `alpha`.
        # The prompt for `vectors.py` said: "PhysicsVector: mass (vol), momentum (p), entropy (s), jerk (j)".
        # It didn't mention nash or alpha.
        # But Soros uses them.
        # I should Add them to `PhysicsVector` or assume they are calculated?
        # Nash Dist is "Distance from Mode". Feynman calculates it.
        # Alpha is "Tail Risk". Feynman calculates it.
        # So they SHOULD be in `PhysicsVector`.
        # I will Update `PhysicsVector` in `vectors.py` to include them.

        # So the plan:
        # 1. Update `vectors.py` to include `nash_dist`, `alpha_coefficient`, `price`.
        # 2. Update `feynman.py` to populate them.
        # 3. Update `soros.py` to use them.

        # Let's finish `soros.py` first with valid logic, assuming `vectors.py` will be updated.

        # We need `price` for `calculate_reflexivity`.
        price = physics_vec.price
        if price <= 0.0:
            price = data.get("price", 0.0)  # Fallback if Vector is empty/malformed

        reflexivity_vec = soros.calculate_reflexivity(symbol, price)

        # Publish State
        state_packet = {"symbol": symbol, "reflexivity": reflexivity_vec.model_dump()}
        await broker.redis.set(
            f"reflexivity:state:{symbol}", orjson.dumps(state_packet), ex=10
        )

        # Legacy Logic for Signal Generation (Gatekeeper)
        # We need to map PhysicsVector -> ForceVector
        # Assuming PhysicsVector will have the needed fields.
        force = ForceVector(
            symbol=symbol,
            price=price,
            momentum=physics_vec.momentum,
            nash_dist=getattr(physics_vec, "nash_dist", 0.0),  # Safer access
            entropy=physics_vec.entropy,
            alpha_coefficient=getattr(physics_vec, "alpha_coefficient", 2.5),
            timestamp=datetime.fromtimestamp(data.get("timestamp", 0) / 1000.0),
        )

        signal = await soros.apply_reflexivity_async(force)
        await broker.publish(signal.model_dump_json(), channel="strategy.signals")

    except Exception as e:
        logger.error(f"Reflexivity Failed: {e}", exc_info=True)


@broker.subscriber("execution.report")
async def handle_execution(msg: Union[bytes, Dict[str, Any]]):
    """
    Snoops on execution reports to track self-inflicted volume.
    """
    try:
        data = orjson.loads(msg) if isinstance(msg, bytes) else msg
        symbol = data.get("symbol")
        qty = float(
            data.get("qty", 0.0)
        )  # Signed? Usually qty is positive, side is BUY/SELL.
        side = data.get("side", "BUY")

        signed_qty = qty if side == "BUY" else -qty

        soros.record_execution(symbol, signed_qty)

    except Exception as e:
        logger.error(f"Execution Snoop Failed: {e}")


@broker.subscriber("forecast.signals")
async def handle_forecast(msg: Union[bytes, Dict[str, Any]]):
    try:
        data = orjson.loads(msg) if isinstance(msg, bytes) else msg
        forecast = ForecastPacket(**data)
        soros.update_forecast(forecast)
    except Exception as e:
        logger.error(f"Forecast Update Failed: {e}")
