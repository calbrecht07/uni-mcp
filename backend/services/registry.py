from supabase import create_client
import os
import json
from services.cache import redis_client
import asyncio



SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
REDIS_URL = os.getenv("REDIS_URL")

#MIGHT NOT BE NEEDED
if not SUPABASE_PROJECT_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials are missing")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL is missing")

supabase = create_client(SUPABASE_PROJECT_URL, SUPABASE_KEY)

async def get_context_registry(user_id: str | None = None) -> list[dict]:
    #Loads all registered context tools (context_types) from Supabase.
    response = supabase.table("context_registry").select("*").execute()
    return response.data or []

async def get_context_registry_cached() -> list[dict]:
    cache_key = "context_registry:all"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    response = supabase.table("context_registry").select("*").execute()
    data = response.data or []
    await redis_client.setex(cache_key, 3600, json.dumps(data))
    return data

async def get_providers_from_registry() -> list[str]:
    registry = await get_context_registry_cached()
    providers = set()
    for entry in registry:
        provider = entry.get("provider")
        if provider:
            providers.add(provider.lower())
    return sorted(providers)

# Handler mapping for dynamic tool registry
from providers.notion import notion_query_database, notion_retrieve_page, notion_search
from providers.slack.slack import slack_search_messages, slack_list_channels, slack_get_channel_messages
from providers.jira.jira_utils import jira_search_issues, jira_create_issue, jira_get_issue, jira_add_comment, jira_update_issue
HANDLER_MAP = {
    "notion_query_database": notion_query_database,
    "notion_retrieve_page": notion_retrieve_page,
    "notion_search": notion_search,
    "slack_search_messages": slack_search_messages,
    "slack_list_channels": slack_list_channels,
    "slack_get_channel_messages": slack_get_channel_messages,
    "jira_search_issues": jira_search_issues,
    "jira_create_issue": jira_create_issue,
    "jira_get_issue": jira_get_issue,
    "jira_add_comment": jira_add_comment,
    "jira_update_issue": jira_update_issue,
}

def get_tool_handler_mapping() -> dict:
    return HANDLER_MAP

async def build_tool_manifest(user_id: str | None = None, providers: list[str] | None = None) -> list[dict]:
    cache_key = f"tool_manifest:{user_id or 'default'}:{'-'.join(providers) if providers else 'all'}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    registry = await get_context_registry(user_id)
    tools = []

    if providers:
        # Only include primary_search tools for the detected providers
        for entry in registry:
            if (
                entry.get("provider", "").lower() in providers
                and entry.get("primary_search", False)
            ):
                tools.append({
                    "type": "function",
                    "function": {
                        "name": entry["name"],
                        "description": entry["description"],
                        "parameters": entry["parameters_schema"]
                    }
                })
    else:
        # No provider detected: include all primary_search tools
        for entry in registry:
            if entry.get("primary_search", False):
                tools.append({
                    "type": "function",
                    "function": {
                        "name": entry["name"],
                        "description": entry["description"],
                        "parameters": entry["parameters_schema"]
                    }
                })

    await redis_client.setex(cache_key, 3600, json.dumps(tools))
    return tools


async def get_primary_search_tools(user_id: str | None = None) -> list[dict]:
    #Fetches and formats tools from the context_registry where primary_search = True
    response = supabase.table("context_registry").select("*").eq("enabled", True).eq("primary_search", True).execute()
    tools = []

    for entry in response.data:
        tools.append({
            "type": "function",
            "function": {
                "name": entry["name"],
                "description": entry["description"],
                "parameters": entry["parameters_schema"]
            }
        })
    # print(f"[Registry] get_primary_search_tools: {tools} \n")
    return tools