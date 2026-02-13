from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
import os
import aiohttp
from supabase import create_client
from datetime import datetime, timedelta

router = APIRouter()

JIRA_CLIENT_ID = os.getenv("JIRA_CLIENT_ID")
JIRA_CLIENT_SECRET = os.getenv("JIRA_CLIENT_SECRET")
JIRA_REDIRECT_URI = os.getenv("JIRA_REDIRECT_URI")
SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

if not SUPABASE_PROJECT_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing Supabase environment variables")

supabase = create_client(SUPABASE_PROJECT_URL, SUPABASE_KEY)

JIRA_AUTH_URL = "https://auth.atlassian.com/authorize"
JIRA_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
JIRA_API_URL = "https://api.atlassian.com"
JIRA_SCOPES = "read:jira-user read:jira-work write:jira-work offline_access"

@router.get("/jira/oauth/authorize")
async def jira_oauth_authorize(user_id: str):
    if not user_id:
        return {"error": "Missing user_id parameter"}
    params = {
        "audience": "api.atlassian.com",
        "client_id": JIRA_CLIENT_ID,
        "scope": JIRA_SCOPES,
        "redirect_uri": JIRA_REDIRECT_URI,
        "state": user_id,
        "response_type": "code",
        "prompt": "consent"
    }
    import urllib.parse
    url = JIRA_AUTH_URL + "?" + urllib.parse.urlencode(params)
    return {"auth_url": url}

@router.get("/jira/oauth/callback")
async def jira_oauth_callback(request: Request):
    code = request.query_params.get("code")
    app_user_id = request.query_params.get("state")
    if not code or not app_user_id:
        return RedirectResponse(url=f"{FRONTEND_URL}/oauth/callback?error=missing_code_or_state")
    # Exchange code for tokens
    data = {
        "grant_type": "authorization_code",
        "client_id": JIRA_CLIENT_ID,
        "client_secret": JIRA_CLIENT_SECRET,
        "code": code,
        "redirect_uri": JIRA_REDIRECT_URI,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(JIRA_TOKEN_URL, json=data, headers={"Content-Type": "application/json"}) as resp:
            token_data = await resp.json()
            print(f"[jira_oauth] Jira token exchange response: {token_data}")
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
    # Get cloud_id and account_id
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{JIRA_API_URL}/oauth/token/accessible-resources", headers={"Authorization": f"Bearer {access_token}"}) as resp:
            resources = await resp.json()
            print(f"[jira_oauth] Jira accessible-resources response: {resources}")
    if not resources or not isinstance(resources, list) or not resources[0].get("id"):
        return RedirectResponse(url=f"{FRONTEND_URL}/oauth/callback?error=no_cloud_id")
    cloud_id = resources[0]["id"]
    # Get Jira user accountId
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{JIRA_API_URL}/ex/jira/{cloud_id}/rest/api/3/myself", headers={"Authorization": f"Bearer {access_token}"}) as resp:
            userinfo = await resp.json()
            print(f"[jira_oauth] Jira myself response: {userinfo}")
    jira_account_id = userinfo.get("accountId")
    # Save to Supabase
    integration_data = {
        "user_id": app_user_id,
        "jira_account_id": jira_account_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at.isoformat(),
        "cloud_id": cloud_id,
    }
    try:
        existing = supabase.table("jira_integration").select("*").eq("user_id", app_user_id).execute()
        if existing.data:
            supabase.table("jira_integration").update(integration_data).eq("user_id", app_user_id).execute()
        else:
            supabase.table("jira_integration").insert(integration_data).execute()
    except Exception as e:
        print(f"[Jira OAuth] Error saving to Supabase: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/oauth/callback?error=supabase_save_failed")
    return RedirectResponse(url=f"{FRONTEND_URL}/oauth/callback?success=jira")

async def get_jira_access_token_and_cloud_id(user_id: str):
    response = supabase.table("jira_integration").select("*").eq("user_id", user_id).execute()
    data = response.data[0] if response.data else None
    if not data:
        print(f"[jira_oauth] No Jira integration found for user_id={user_id}")
        return None, None
    return data.get("access_token"), data.get("cloud_id") 