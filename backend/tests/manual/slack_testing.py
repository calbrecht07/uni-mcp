import os
import asyncio
import aiohttp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Extract Slack OAuth token from environment
SLACK_OAUTH_TOKEN = os.getenv("SLACK_OAUTH_TOKEN")


async def get_token():
    """
    Retrieves the static OAuth token from environment.
    """
    return SLACK_OAUTH_TOKEN


async def test_api_call(access_token):
    """
    Makes a basic API call to Slack using the access token.
    For demonstration, it lists public conversations.
    """
    url = "https://slack.com/api/conversations.list"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            print("Response from Slack API call:")
            print(data)


if __name__ == "__main__":
    print("Testing Slack API call using static OAuth token...")

    async def run():
        token = await get_token()
        if token:
            await test_api_call(token)
        else:
            print("OAuth token missing or invalid.")

    asyncio.run(run())