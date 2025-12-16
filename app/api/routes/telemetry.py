from litestar import Controller, WebSocket, websocket
from app.services.state_stream import get_state_broadcaster
import logging

logger = logging.getLogger(__name__)


class TelemetryController(Controller):
    path = "/ws"

    @websocket("/stream")
    async def stream_status(self, socket: WebSocket) -> None:
        """
        WebSocket endpoint for streaming real-time agent state.
        Path: /ws/stream
        """
        await socket.accept()
        broadcaster = get_state_broadcaster()
        queue = broadcaster.subscribe()

        try:
            while True:
                # Wait for next state update
                data = await queue.get()
                await socket.send_json(data)
        except Exception as e:
            logger.info(f"WebSocket disconnected: {e}")
        finally:
            broadcaster.unsubscribe(queue)
            try:
                await socket.close()
            except Exception:
                pass
