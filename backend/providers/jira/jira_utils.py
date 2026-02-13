import re
from services.llm.phi3_intent import ensure_ollama_running
import httpx
import aiohttp
import os
from providers.jira.jira_oauth import get_jira_access_token_and_cloud_id

JIRA_API_URL = "https://api.atlassian.com"


def prompt_to_jql(prompt: str) -> str:
    """
    Convert a natural language prompt into a simple JQL query.
    This is a basic version using heuristics and keyword mapping.
    """
    prompt = prompt.lower()
    jql_parts = []
    match = re.search(r"(about|for|on|related to|regarding)\s+(the\s+)?([a-zA-Z0-9\s\-]+)", prompt)
    if match:
        keyword = match.group(3).strip()
        jql_parts.append(f'text ~ "{keyword}"')

    # Status detection
    if "open" in prompt or "in progress" in prompt:
        jql_parts.append('status in ("Open", "In Progress")')
    elif "closed" in prompt or "done" in prompt:
        jql_parts.append('status in ("Done", "Closed")')

    # Assignee detection
    assignee_match = re.search(r"(assigned to|by)\s+([a-zA-Z0-9_]+)", prompt)
    if assignee_match:
        assignee = assignee_match.group(2)
        jql_parts.append(f'assignee = "{assignee}"')

    # Project detection
    project_match = re.search(r"in project ([A-Z0-9\-]+)", prompt)
    if project_match:
        project = project_match.group(1)
        jql_parts.insert(0, f'project = "{project}"')

    # Default fallback if no parts found
    if not jql_parts:
        jql_parts.append(f'text ~ "{prompt.strip()}"')
    return " AND ".join(jql_parts)


async def prompt_to_jql_phi3(prompt: str) -> str:
    """
    Use phi3 via Ollama to generate a JQL query from a natural language prompt.
    Returns the JQL string or falls back to the original prompt if LLM fails.
    """
    await ensure_ollama_running()
    FEW_SHOT = '''  Convert the following user request into a Jira JQL query. Output only the JQL.

                    User: Show me all open bugs assigned to Alice in project X.
                    JQL: project = "X" AND status = "Open" AND issuetype = "Bug" AND assignee = "Alice"

                    User: List closed tasks in project Y.
                    JQL: project = "Y" AND status = "Closed" AND issuetype = "Task"

                    User: Find tickets about onboarding in project ABC.
                    JQL: project = "ABC" AND text ~ "onboarding"

                    User: {prompt}
                    JQL:'''
                    
    full_prompt = FEW_SHOT.format(prompt=prompt.strip().replace('"', ''))
    payload = {
        "model": "phi3:mini",
        "prompt": full_prompt,
        "stream": True
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            async with client.stream("POST", "http://localhost:11434/api/generate", json=payload) as response:
                jql = ""
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = httpx.Response(200, content=line).json()
                        chunk = data.get("response", "")
                        jql += chunk
                    except Exception:
                        continue
                # Extract the first line or up to a newline as the JQL
                jql = jql.strip().split("\n")[0]
                # Remove any leading/trailing 'JQL:'
                jql = jql.replace("JQL:", "").strip()
                return jql if jql else prompt
    except Exception as e:
        print(f"[jira_utils] ERROR: LLM JQL generation failed: {e}")
        return prompt



async def jira_search_issues(parameters: dict) -> dict:
    """
    Perform a Jira issue search using the provided parameters dict.
    Expects 'cloud_id', 'jql', and 'access_token' in parameters.
    Prints and returns the API response.
    """
    print(f"[jira_search_issues] Called with parameters: {parameters}")
    cloud_id = parameters.get("cloud_id")
    jql = parameters.get("jql")
    access_token = parameters.get("access_token")
    user_id = parameters.get("user_id")
    if (not access_token or not cloud_id) and user_id:
        access_token, cloud_id = await get_jira_access_token_and_cloud_id(user_id)
    if not cloud_id or not jql or not access_token:
        return {"error": "Missing required parameters: cloud_id, jql, access_token, or user_id"}
    url = f"{JIRA_API_URL}/ex/jira/{cloud_id}/rest/api/3/search"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    params = {"jql": jql}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            response_json = await resp.json()
            print(f"[jira_search_issues] Jira API response: {response_json}")
            if 'error' in response_json:
                print(f"[jira_search_issues] Jira API error: {response_json['error']}")
            if 'message' in response_json:
                print(f"[jira_search_issues] Jira API message: {response_json['message']}")
            return response_json


async def jira_create_issue(parameters: dict) -> dict:
    """
    Create a new Jira issue (ticket) in a specified project.
    Expects 'cloud_id', 'access_token', and required fields in parameters.
    """
    print(f"[jira_create_issue] Called with parameters: {parameters}")
    cloud_id = parameters.get("cloud_id")
    access_token = parameters.get("access_token")
    user_id = parameters.get("user_id")
    if (not access_token or not cloud_id) and user_id:
        access_token, cloud_id = await get_jira_access_token_and_cloud_id(user_id)
    # TODO: Extract required fields: projectKey, summary, description, issueType, etc.
    fields = parameters.get("fields")  # Should be a dict with Jira issue fields
    if not cloud_id or not access_token or not fields:
        return {"error": "Missing required parameters: cloud_id, access_token, fields, or user_id"}
    url = f"{JIRA_API_URL}/ex/jira/{cloud_id}/rest/api/3/issue"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    body = {"fields": fields}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as resp:
            response_json = await resp.json()
            print(f"[jira_create_issue] Jira API response: {response_json}")
            if 'error' in response_json:
                print(f"[jira_create_issue] Jira API error: {response_json['error']}")
            if 'message' in response_json:
                print(f"[jira_create_issue] Jira API message: {response_json['message']}")
            return response_json


async def jira_get_issue(parameters: dict) -> dict:
    """
    Retrieve details of a Jira issue by its key.
    Expects 'cloud_id', 'access_token', and 'issue_id' (or 'issue_key') in parameters.
    """
    print(f"[jira_get_issue] Called with parameters: {parameters}")
    cloud_id = parameters.get("cloud_id")
    access_token = parameters.get("access_token")
    user_id = parameters.get("user_id")
    if (not access_token or not cloud_id) and user_id:
        access_token, cloud_id = await get_jira_access_token_and_cloud_id(user_id)
    issue_id = parameters.get("issue_id") or parameters.get("issue_key")
    if not cloud_id or not access_token or not issue_id:
        return {"error": "Missing required parameters: cloud_id, access_token, issue_id/issue_key, or user_id"}
    url = f"{JIRA_API_URL}/ex/jira/{cloud_id}/rest/api/3/issue/{issue_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            response_json = await resp.json()
            print(f"[jira_get_issue] Jira API response: {response_json}")
            if 'error' in response_json:
                print(f"[jira_get_issue] Jira API error: {response_json['error']}")
            if 'message' in response_json:
                print(f"[jira_get_issue] Jira API message: {response_json['message']}")
            return response_json



async def jira_add_comment(parameters: dict) -> dict:
    """
    Add a comment to a Jira issue.
    Expects 'cloud_id', 'access_token', 'issue_id' (or 'issue_key'), and 'comment' in parameters.
    """
    print(f"[jira_add_comment] Called with parameters: {parameters}")
    cloud_id = parameters.get("cloud_id")
    access_token = parameters.get("access_token")
    user_id = parameters.get("user_id")
    if (not access_token or not cloud_id) and user_id:
        access_token, cloud_id = await get_jira_access_token_and_cloud_id(user_id)
    issue_id = parameters.get("issue_id") or parameters.get("issue_key")
    comment = parameters.get("comment")
    if not cloud_id or not access_token or not issue_id or not comment:
        return {"error": "Missing required parameters: cloud_id, access_token, issue_id/issue_key, comment, or user_id"}
    url = f"{JIRA_API_URL}/ex/jira/{cloud_id}/rest/api/3/issue/{issue_id}/comment"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    body = {"body": comment}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as resp:
            response_json = await resp.json()
            print(f"[jira_add_comment] Jira API response: {response_json}")
            if 'error' in response_json:
                print(f"[jira_add_comment] Jira API error: {response_json['error']}")
            if 'message' in response_json:
                print(f"[jira_add_comment] Jira API message: {response_json['message']}")
            return response_json



async def jira_update_issue(parameters: dict) -> dict:
    """
    Update fields of an existing Jira issue.
    Expects 'cloud_id', 'access_token', 'issue_id' (or 'issue_key'), and 'fields' (dict) in parameters.
    """
    print(f"[jira_update_issue] Called with parameters: {parameters}")
    cloud_id = parameters.get("cloud_id")
    access_token = parameters.get("access_token")
    user_id = parameters.get("user_id")
    if (not access_token or not cloud_id) and user_id:
        access_token, cloud_id = await get_jira_access_token_and_cloud_id(user_id)
    issue_id = parameters.get("issue_id") or parameters.get("issue_key")
    fields = parameters.get("fields")
    if not cloud_id or not access_token or not issue_id or not fields:
        return {"error": "Missing required parameters: cloud_id, access_token, issue_id/issue_key, fields, or user_id"}
    url = f"{JIRA_API_URL}/ex/jira/{cloud_id}/rest/api/3/issue/{issue_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    body = {"fields": fields}
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, json=body) as resp:
            response_json = await resp.json()
            print(f"[jira_update_issue] Jira API response: {response_json}")
            if 'error' in response_json:
                print(f"[jira_update_issue] Jira API error: {response_json['error']}")
            if 'message' in response_json:
                print(f"[jira_update_issue] Jira API message: {response_json['message']}")
            return response_json