import asyncio
import logging
from collections import deque
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class StateBroadcaster:
    """
    In-memory State Broadcaster for broadcasting agent state updates to subscribers (e.g., WebSockets).
    Singleton pattern ensures all parts of the app access the same bus.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateBroadcaster, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._subscribers: List[asyncio.Queue] = []
        self._history = deque(maxlen=10)  # Store last 10 states for replay
        self._initialized = True
        logger.info("📡 StateBroadcaster initialized")

    async def broadcast(self, state: dict):
        """
        Broadcast a state update to all subscribers.
        """
        # Append to history for new joiners
        self._history.append(state)

        # Broadcast to all active queues
        if not self._subscribers:
            return

        # Removing closed queues is handled during consumption usually,
        # but here we just push. If a queue is full or closed, we might handle exceptions.
        # For simple in-memory, just put_nowait or await put.
        # using await put ensures flow control if queues have maxsize.

        for queue in self._subscribers:
            try:
                # We use put_nowait to avoid blocking the broadcaster if a single client is slow.
                # If queue is full, this raises asyncio.QueueFull, which we can ignore or log.
                queue.put_nowait(state)
            except asyncio.QueueFull:
                logger.warning(
                    "StateBroadcaster: A subscriber queue is full. Dropping message for them."
                )
            except Exception as e:
                logger.error(f"StateBroadcaster: Error broadcasting to queue: {e}")

    def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to state updates. Returns an asyncio.Queue.
        Replays the last 10 states immediately.
        """
        # Create new queue for this client
        queue = asyncio.Queue(maxsize=100)  # Buffer size

        # Replay history
        for state in self._history:
            try:
                queue.put_nowait(state)
            except asyncio.QueueFull:
                pass  # Should not happen with new queue and maxlen=10

        self._subscribers.append(queue)
        logger.debug(
            f"StateBroadcaster: New subscriber. Total: {len(self._subscribers)}"
        )
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """
        Unsubscribe a queue.
        """
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            logger.debug(
                f"StateBroadcaster: Unsubscribed. Total: {len(self._subscribers)}"
            )


# Global Instance Accessor
_broadcaster = StateBroadcaster()


def get_state_broadcaster() -> StateBroadcaster:
    """
    Returns the singleton StateBroadcaster instance.
    """
    return _broadcaster
