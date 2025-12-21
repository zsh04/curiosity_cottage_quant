import os
import logging
import orjson
import aiohttp
from datetime import datetime
from typing import Optional, Union, Dict, Any
from faststream import FastStream
from faststream.redis import RedisBroker
from app.core.models import ForceVector, TradeSignal, Side, ForecastPacket

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

    def __init__(self):
        self.latest_forecast: Optional[ForecastPacket] = None
        self.ollama_url = os.getenv(
            "OLLAMA_URL", "http://host.docker.internal:11434/api/generate"
        )
        self.model_name = os.getenv("OLLAMA_MODEL", "llama3")
        self.macro_agent = MacroAgent()

    def update_forecast(self, forecast: ForecastPacket):
        self.latest_forecast = forecast

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
        payload = {
            "timestamp": datetime.fromtimestamp(data.get("timestamp", 0) / 1000.0)
            if isinstance(data.get("timestamp"), (int, float))
            else datetime.now(),
            "symbol": data.get("symbol"),
            **vectors,
        }
        force = ForceVector(**payload)

        # Use the Async method now
        signal = await soros.apply_reflexivity_async(force)

        await broker.publish(signal.model_dump_json(), channel="strategy.signals")

    except Exception as e:
        logger.error(f"Reflexivity Failed: {e}", exc_info=True)
        # PANIC RECOVERY
        # If we failed here, we should probably emit a HOLD signal to indicate ERROR state
        # But we might struggle to construct a valid signal without a symbol.
        # Fallback effort:
        try:
            if isinstance(msg, (bytes, str, dict)):
                # Try simple recovery
                data = orjson.loads(msg) if isinstance(msg, bytes) else msg
                symbol = data.get("symbol", "UNKNOWN")
                err_signal = TradeSignal(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    side=Side.HOLD,
                    strength=0.0,
                    price=0.0,
                    meta={"warning": "INTERNAL_ERROR", "error": str(e)},
                )
                await broker.publish(
                    err_signal.model_dump_json(), channel="strategy.signals"
                )
        except:
            logger.critical("Double Fault in Reflexivity Handler. Signal Lost.")


@broker.subscriber("forecast.signals")
async def handle_forecast(msg: Union[bytes, Dict[str, Any]]):
    try:
        data = orjson.loads(msg) if isinstance(msg, bytes) else msg
        forecast = ForecastPacket(**data)
        soros.update_forecast(forecast)
    except Exception as e:
        logger.error(f"Forecast Update Failed: {e}")
