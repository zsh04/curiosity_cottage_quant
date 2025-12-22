from litestar import Controller, post, WebSocket, get
from litestar.handlers import WebsocketListener
from litestar.background_tasks import BackgroundTask
from redis.asyncio import Redis
import os
import uuid
import asyncio
import logging
import orjson
from datetime import datetime

from app.services.backtest import BacktestEngine
from app.dal.backtest import BacktestDAL

logger = logging.getLogger("ShannonChannel")


# Background Worker
async def run_backtest_task(run_id: str, start_date: str, end_date: str):
    logger.info(f"🚀 Starting Backtest {run_id} ({start_date} to {end_date})")

    # 1. Spawn Log
    dal = BacktestDAL()
    await dal.log_spawn(run_id, "ALL_ASSETS", {"start": start_date, "end": end_date})

    # 2. Init & Load
    engine = BacktestEngine(start_date, end_date, run_id=run_id)
    # Note: load_data is sync currently in BacktestEngine, which blocks the event loop thread!
    # Ideally should be async or run in thread. For now, since this is a backtest job,
    # and we are inside a background task, blocking the thread isn't catastrophic
    # but could stall other requests if running on same loop.
    # For MVP, we proceed.
    engine.load_data()

    # 3. Run
    await engine.run()
    logger.info(f"🏁 Backtest {run_id} Finished.")


class BacktestController(Controller):
    path = "/backtest"

    @post("/spawn")
    async def spawn_simulation(self, data: dict) -> dict:
        """
        Start a new backtest simulation.
        Payload: {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
        """
        run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
        start = data.get("start_date", "2024-01-01")
        end = data.get("end_date", "2024-01-31")

        # Start Background Task
        # Litestar handles background tasks via return usually, or we can use asyncio.create_task independent of request life
        asyncio.create_task(run_backtest_task(run_id, start, end))

        return {"run_id": run_id, "status": "spawned"}


class BacktestStream(WebsocketListener):
    path = "/backtest/stream/{run_id:str}"

    async def on_accept(self, socket: WebSocket, run_id: str) -> None:
        logger.info(f"📡 Client listening to {run_id}")

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        client = Redis.from_url(redis_url, decode_responses=False)
        pubsub = client.pubsub()
        await pubsub.subscribe(f"backtest:{run_id}")

        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message:
                    # Raw bytes pass-through for speed
                    await socket.send_text(message["data"].decode("utf-8"))

                    # Check if completed to close?
                    # The client should close, but we can verify payload
                    try:
                        payload = orjson.loads(message["data"])
                        if payload.get("type") in ["COMPLETED", "FAILED"]:
                            # Allow client to read it then close?
                            # Or just keep open. Let's keep open for a moment.
                            pass
                    except:
                        pass
                else:
                    await asyncio.sleep(0.01)

        except Exception as e:
            logger.warning(f"Stream Disconnected: {e}")
        finally:
            await pubsub.unsubscribe()
            await client.close()

    async def on_disconnect(self, socket: WebSocket) -> None:
        pass
