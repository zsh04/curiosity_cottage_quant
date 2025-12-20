import asyncio
import redis.asyncio as redis
import socket


async def verify_dragonfly():
    print("--- Verifying Dragonfly (Hot State) ---")
    try:
        # Dragonfly compatible with Redis protocol
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        await r.set("ezekiel:test", "alive")
        val = await r.get("ezekiel:test")
        if val == "alive":
            print("✅ Dragonfly Connection: SUCCESS")
            info = await r.info()
            print(f"   Server: {info.get('redis_version', 'Unknown')} (Dragonfly)")
        else:
            print("❌ Dragonfly Connection: FAILED (Value mismatch)")
        await r.close()
    except Exception as e:
        print(f"❌ Dragonfly Connection: FAILED ({e})")


def verify_questdb():
    print("\n--- Verifying QuestDB (Cold Storage) ---")
    # Verify ILP Port (9000) and PG Wire (8812) are open
    for port, name in [(9000, "ILP"), (8812, "PG Wire"), (9003, "Console")]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("localhost", port))
            if result == 0:
                print(f"✅ QuestDB {name} Port ({port}): OPEN")
            else:
                print(f"❌ QuestDB {name} Port ({port}): CLOSED")
            sock.close()
        except Exception as e:
            print(f"❌ QuestDB {name} Port ({port}): ERROR ({e})")


async def main():
    print("🦅 PROJECT EZEKIEL: SYSTEMS CHECK 🦅")
    await verify_dragonfly()
    verify_questdb()


if __name__ == "__main__":
    try:
        import uvloop

        uvloop.install()
    except ImportError:
        print("⚠️ uvloop not found, using default asyncio loop")

    asyncio.run(main())
