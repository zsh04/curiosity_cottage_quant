#!/usr/bin/env python3
"""
Quick test script to verify WebSocket endpoint is accessible.
"""

import asyncio
import websockets
import json


async def test_websocket():
    uri = "ws://localhost:8000/api/ws/stream"
    print(f"🔌 Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            print("📡 Waiting for telemetry...")

            # Receive 3 messages
            for i in range(3):
                message = await websocket.recv()
                data = json.loads(message)
                print(f"\n📦 Packet {i + 1}:")
                print(f"  Market: {data.get('market', {}).get('symbol', 'N/A')}")
                print(f"  Price: ${data.get('market', {}).get('price', 0.0)}")
                print(f"  Alpha: {data.get('market', {}).get('alpha', 0.0)}")
                print(f"  Signal: {data.get('signal', {}).get('side', 'N/A')}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
