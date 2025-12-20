from litestar import WebSocket, websocket_listener
from litestar.handlers import WebsocketListener
from app.services.state_stream import get_state_broadcaster
from app.services.redis_bridge import RedisBridge
import logging
import asyncio

logger = logging.getLogger(__name__)


class BrainStream(WebsocketListener):
    path = "/ws/stream"

    async def on_accept(self, socket: WebSocket) -> None:
        """
        Called when a client connects.
        Subscribes to the internal StateBroadcaster and pipes events to the socket.
        """
        logger.info(f"🧠 BrainStream: Client Connected")

        # Lazy Start the Watchtower Bridge
        bridge = RedisBridge.get_instance()
        if not bridge.running:
            await bridge.start()

        # Subscribe to internal bus
        broadcaster = get_state_broadcaster()
        queue = broadcaster.subscribe()

        try:
            while True:
                # Wait for internal event
                data = await queue.get()

                # Forward to WebSocket client
                # Litestar handles JSON serialization
                await socket.send_json(data)

        except Exception as e:
            logger.warning(f"🧠 BrainStream: Connection Closed ({e})")
        finally:
            broadcaster.unsubscribe(queue)

    async def on_disconnect(self, socket: WebSocket) -> None:
        logger.info("🧠 BrainStream: Client Disconnected")

    async def on_receive(self, data: str, socket: WebSocket) -> None:
        """
        Handle incoming messages from client (e.g. ping/pong, config updates).
        """
        logger.debug(f"🧠 BrainStream: Received {data}")
