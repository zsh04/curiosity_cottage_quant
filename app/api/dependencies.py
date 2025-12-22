from redis.asyncio import Redis
import os


async def get_redis_client() -> Redis:
    """
    Dependency: Get Async Redis Client.
    """
    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return Redis.from_url(url, decode_responses=True)
