import pytest
import asyncio
import orjson
from unittest.mock import AsyncMock, patch
from app.services.redis_bridge import RedisBridge
from app.services.state_stream import get_state_broadcaster


@pytest.mark.asyncio
async def test_watchtower_flow():
    """
    Test that Redis messages are transformed and broadcasted.
    """
    bridge = RedisBridge.get_instance()
    broadcaster = get_state_broadcaster()

    # Mock Redis PubSub
    mock_redis = AsyncMock()
    mock_pubsub = AsyncMock()

    # Setup mock message sequence
    # 1. Physics Message
    physics_msg = {
        "channel": b"physics.forces",
        "data": orjson.dumps(
            {
                "symbol": "BTC",
                "vectors": {
                    "alpha_coefficient": 2.5,
                    "momentum": 100.0,
                    "price": 50000.0,
                },
            }
        ),
    }

    # Mocking get_message to return physics_msg once then behave like queue empty or stop
    # In integration we want to see it hit the broadcaster.

    # Let's directly test _process_message logic
    await bridge._process_message(physics_msg, broadcaster)

    # Assert Broadcaster received it
    queue = broadcaster.subscribe()
    packet = await queue.get()

    assert packet["source"] == "watchtower"
    assert "market" in packet
    assert packet["market"]["symbol"] == "BTC"
    assert packet["market"]["regime"] == "GAUSSIAN (Safe)"
    assert packet["market"]["price"] == 50000.0

    # 2. Strategy Message
    strategy_msg = {
        "channel": b"strategy.signals",
        "data": orjson.dumps(
            {"side": "BUY", "strength": 0.9, "meta": {"reason": "Test"}}
        ),
    }

    await bridge._process_message(strategy_msg, broadcaster)
    packet2 = await queue.get()

    assert "signal" in packet2
    assert packet2["signal"]["side"] == "BUY"
    assert packet2["signal"]["score"] == 0.9

    broadcaster.unsubscribe(queue)
