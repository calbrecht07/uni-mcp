import os
import aiohttp
from services.cache import redis_client
from typing import Optional

class TokenManager:
    def __init__(self, service_name: str, refresh_url: str, refresh_payload: dict, token_field: str = "access_token", ttl: int = 7000):
        self.cache_key = f"access_token:{service_name}"
        self.refresh_url = refresh_url
        self.refresh_payload = refresh_payload
        self.token_field = token_field
        self.ttl = ttl

    async def get_token(self) -> str:
        cached = await redis_client.get(self.cache_key)
        if cached:
            return cached

        headers = { "Content-Type": "application/x-www-form-urlencoded" }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.refresh_url, data=self.refresh_payload, headers=headers) as resp:
                data = await resp.json()
                print(f"------>> Token refresh response: {data}")
                if not data.get("ok"):
                    raise Exception(f"Token refresh failed: {data}")
                token = data[self.token_field]
                await redis_client.set(self.cache_key, token, ex=self.ttl)
                return token