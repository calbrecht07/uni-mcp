import os
import aiohttp
from typing import Any
from providers.slack.slack_oauth import get_valid_user_access_token
import re
import nltk
from nltk.corpus import stopwords

# Ensure stopwords are downloaded (run once)
try:
    stop_words = set(stopwords.words('english'))
except LookupError:
    nltk.download('stopwords')
    stop_words = set(stopwords.words('english'))

def extract_keywords_nltk(text):
    text = re.sub(r'[^\w\s]', '', text.lower())
    words = text.split()
    removed = [word for word in words if word in stop_words]
    keywords = [word for word in words if word not in stop_words]
    print("\n--- [Slack] ---", flush=True)
    print(f"[Slack Keyword Extractor] Removed stopwords: {removed}", flush=True)
    return ' '.join(keywords)

SLACK_API_BASE_URL = "https://slack.com/api"


async def slack_search_messages(parameters: dict[str, Any]) -> dict:
    slack_user_id = parameters.get("slack_user_id")
    app_user_id = parameters.get("app_user_id")
    if not slack_user_id:
        print("\n--- [Slack] ---", flush=True)
        print("[Slack] missing slack_user_id in parameters, cannot search messages.", flush=True)
        return {"ok": False, "error": "missing_slack_user_id"}
    token_result = await get_valid_user_access_token(slack_user_id, app_user_id)
    # print(f"[Slack] token_result: {token_result}")
    if isinstance(token_result, dict) and token_result.get("auth_required"):
        print("\n--- [Slack] ---", flush=True)
        print("[Slack] User needs to authorize Slack, redirecting to auth URL.", flush=True)
        return {"ok": False, "error": "slack_auth_required", "auth_url": token_result["auth_url"]}
    SLACK_API_TOKEN = token_result["access_token"] if isinstance(token_result, dict) else token_result
    if not SLACK_API_TOKEN:
        print("\n--- [Slack] ---", flush=True)
        print("[Slack] Missing or invalid Slack API token.", flush=True)
        return {"ok": False, "error": "missing_or_invalid_token"}
    # Backend enforcement: always reduce query to keywords using NLTK
    raw_query = parameters["query"]
    search_query = extract_keywords_nltk(raw_query)
    print("\n--- [Slack] ---", flush=True)
    print(f"[Slack Enforcement] Final search query: {search_query}", flush=True)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{SLACK_API_BASE_URL}/search.messages",
            headers={"Authorization": f"Bearer {SLACK_API_TOKEN}"},
            params={"query": search_query}
        ) as response:
            resp_json = await response.json()
            if response.status != 200:
                print("\n--- [Slack] ---", flush=True)
                print(f"Slack API error: {response.status} - {resp_json}", flush=True)
                return {"ok": False, "error": "slack_api_error", "status": response.status}
            print("\n--- [Slack] ---", flush=True)
            print(f"[Slack API] search.messages response: {resp_json}", flush=True)
            return resp_json


async def slack_list_channels(parameters: dict[str, Any]) -> dict:
    slack_user_id = parameters.get("slack_user_id")
    app_user_id = parameters.get("app_user_id")
    if not slack_user_id:
        return {"ok": False, "error": "missing_slack_user_id"}
    token_result = await get_valid_user_access_token(slack_user_id, app_user_id)
    if isinstance(token_result, dict) and token_result.get("auth_required"):
        return {"ok": False, "error": "slack_auth_required", "auth_url": token_result["auth_url"]}
    SLACK_API_TOKEN = token_result["access_token"] if isinstance(token_result, dict) else token_result
    if not SLACK_API_TOKEN:
        return {"ok": False, "error": "missing_or_invalid_token"}
    print("\n--- [Slack] ---", flush=True)
    print(f"Searching Slack list channels\n", flush=True)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{SLACK_API_BASE_URL}/conversations.list",
            headers={"Authorization": f"Bearer {SLACK_API_TOKEN}"}
        ) as response:
            return await response.json()


async def slack_get_channel_messages(parameters: dict[str, Any]) -> dict:
    limit = parameters.get("limit", 10)
    slack_user_id = parameters.get("slack_user_id")
    app_user_id = parameters.get("app_user_id")
    if not slack_user_id:
        return {"ok": False, "error": "missing_slack_user_id"}
    token_result = await get_valid_user_access_token(slack_user_id, app_user_id)
    if isinstance(token_result, dict) and token_result.get("auth_required"):
        return {"ok": False, "error": "slack_auth_required", "auth_url": token_result["auth_url"]}
    SLACK_API_TOKEN = token_result["access_token"] if isinstance(token_result, dict) else token_result
    if not SLACK_API_TOKEN:
        return {"ok": False, "error": "missing_or_invalid_token"}
    print("\n--- [Slack] ---", flush=True)
    print(f"Searching get channel with query: {parameters.get('query')}\n", flush=True)

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{SLACK_API_BASE_URL}/conversations.history",
            headers={"Authorization": f"Bearer {SLACK_API_TOKEN}"},
            params={"channel": parameters["channel_id"], "limit": limit}
        ) as response:
            return await response.json()