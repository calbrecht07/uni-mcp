import asyncio
from services.cache import redis_client

async def check_mapping(app_user_id):
    slack_user_id = await redis_client.get(f"app_to_slack_user:{app_user_id}")
    print(f"app_to_slack_user:{app_user_id} -> {slack_user_id}")

if __name__ == "__main__":
    asyncio.run(check_mapping("test-user-123"))