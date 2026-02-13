import httpx
from typing import Optional, Dict, Any
import os

#BEARER TOKEN NEEDS TO BE DELETED WHEN FRONTEND IS READY
token = os.getenv("NOTION_CLIENT_SECRET")


NOTION_API_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"

async def notion_query_database(
    database_id: str,
    token: str,
    filter: Optional[Dict[str, Any]] = None,
    sorts: Optional[list] = None
) -> Dict[str, Any]:
    """
    Calls the Notion API to query a database.
    Accepts database_id and optional filter/sorts.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json"
    }

    body = {}
    if filter:
        body["filter"] = filter
    if sorts:
        body["sorts"] = sorts

    url = f"{NOTION_API_URL}/databases/{database_id}/query"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"Notion API error: {str(e)}", "details": e.response.text}

async def notion_search(
    query: str,
    filter: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Search all Notion pages and databases shared with this integration.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json"
    }

    body = {
        "query": query
    }
    if filter:
        body["filter"] = filter

    url = f"{NOTION_API_URL}/search"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"Notion API error: {str(e)}", "details": e.response.text}
    
async def notion_retrieve_page(
    page_id: str,
    token: str
) -> Dict[str, Any]:
    """
    Retrieve metadata about a Notion page.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION
    }

    url = f"{NOTION_API_URL}/pages/{page_id}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"Notion API error: {str(e)}", "details": e.response.text}