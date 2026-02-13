import asyncio
import os
from redis.asyncio import Redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL is missing")

async def test_redis():
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis.set("test_key", "hello_redis")
        value = await redis.get("test_key")
        print("Redis connection successful! test_key value:", value)
        await redis.delete("test_key")
    except Exception as e:
        print("Redis connection failed:", e) 
    finally:
        await redis.aclose()

if __name__ == "__main__":
    asyncio.run(test_redis())