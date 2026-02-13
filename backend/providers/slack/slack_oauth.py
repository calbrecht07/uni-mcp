from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from services.cache import redis_client
import json
import aiohttp
import os
import time
from supabase import create_client
from datetime import datetime, timedelta

router = APIRouter()

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI")
SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

if not SLACK_CLIENT_ID or not SLACK_CLIENT_SECRET or not SLACK_REDIRECT_URI:
    raise RuntimeError("Missing Slack OAuth environment variables")

if not SUPABASE_PROJECT_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing Supabase environment variables")

supabase = create_client(SUPABASE_PROJECT_URL, SUPABASE_KEY)

# Replace this with your own token storage logic (e.g. Redis, DB, file)
user_tokens = {}

async def save_user_oauth_token_to_supabase(token_data, app_user_id):
    """Save Slack OAuth tokens to Supabase slack_integration table"""
    slack_user_id = token_data.get("authed_user", {}).get("id")
    if not slack_user_id or not app_user_id:
        print(f"[Slack OAuth] Missing user IDs: slack_user_id={slack_user_id}, app_user_id={app_user_id}")
        return False
    
    expires_in = token_data.get("authed_user", {}).get("expires_in", 43200)
    expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # 60s buffer
    
    integration_data = {
        "user_id": app_user_id,
        "slack_user_id": slack_user_id,
        "bot_access_token": token_data.get("access_token"),
        "user_access_token": token_data.get("authed_user", {}).get("access_token"),
        "bot_refresh_token": token_data.get("refresh_token"),
        "user_refresh_token": token_data.get("authed_user", {}).get("refresh_token"),
        "scope": token_data.get("authed_user", {}).get("scope"),
        "expires_at": expires_at.isoformat(),  # Convert to ISO format string
    }
    
    try:
        # Check if integration already exists
        existing = supabase.table("slack_integration").select("*").eq("user_id", app_user_id).execute()
        
        if existing.data:
            # Update existing integration
            result = supabase.table("slack_integration").update(integration_data).eq("user_id", app_user_id).execute()
        else:
            # Insert new integration
            result = supabase.table("slack_integration").insert(integration_data).execute()
        
        print(f"[Slack OAuth] Saved to Supabase for app_user_id: {app_user_id}, slack_user_id: {slack_user_id}")
        return True
    except Exception as e:
        print(f"[Slack OAuth] Error saving to Supabase: {e}")
        return False

async def save_user_oauth_token(token_data):
    user_id = token_data.get("authed_user", {}).get("id")
    if user_id:
        expires_in = token_data.get("authed_user", {}).get("expires_in", 43200)
        expires_at = int(time.time()) + expires_in - 60  # 60s buffer
        token_info = {
            "bot_access_token": token_data.get("access_token"),
            "user_access_token": token_data.get("authed_user", {}).get("access_token"),
            "refresh_token": token_data.get("authed_user", {}).get("refresh_token"),
            "scope": token_data.get("authed_user", {}).get("scope"),
            "expires_at": expires_at,
        }
        print(f"Token info for user {user_id}: {token_info}")
        await redis_client.setex(
            f"slack_user_token:{user_id}",
            expires_in,
            json.dumps(token_info)
        )
        print(f"[Slack OAuth] Token saved to Redis for Slack user_id: {user_id} (expires in {expires_in}s)")
        # Store bot token globally for local dev (12 hours)
        bot_token = token_data.get("access_token")
        if bot_token:
            await redis_client.setex(
                "slack_bot_access_token",
                43200,  # 12 hours
                bot_token
            )
            print(f"[Slack OAuth] Bot access token saved to Redis (12h TTL)")

async def get_user_oauth_token(user_id: str, token_type="user"):
    token_json = await redis_client.get(f"slack_user_token:{user_id}")
    if not token_json:
        print(f"[Slack OAuth] No token found in Redis for Slack user_id: {user_id}")
        return None
    print(f"[Slack OAuth] Token retrieved from Redis for Slack user_id: {user_id}")
    token_info = json.loads(token_json)
    if token_type == "user":
        return token_info.get("user_access_token")
    else:
        return token_info.get("bot_access_token")

@router.get("/oauth/authorize")
async def oauth_authorize(user_id: str):
    """Generate Slack OAuth URL for the given user"""
    if not user_id:
        return {"error": "Missing user_id parameter"}
    
    auth_url = get_slack_oauth_authorize_url(user_id)
    return {"auth_url": auth_url}

@router.get("/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")
    app_user_id = request.query_params.get("state")  # <-- get app user id from state
    
    if not code:
        # Redirect to frontend with error
        return RedirectResponse(url=f"{FRONTEND_URL}/oauth/callback?error=missing_code")
    
    if not app_user_id:
        # Redirect to frontend with error
        return RedirectResponse(url=f"{FRONTEND_URL}/oauth/callback?error=missing_state")

    token_url = "https://slack.com/api/oauth.v2.access"
    data = {
        "client_id": SLACK_CLIENT_ID,
        "client_secret": SLACK_CLIENT_SECRET,
        "code": code,
        "redirect_uri": SLACK_REDIRECT_URI,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=data) as response:
            token_data = await response.json()
            print("Slack token response:", token_data)

            if token_data.get("ok"):
                # Save to Supabase instead of Redis
                success = await save_user_oauth_token_to_supabase(token_data, app_user_id)
                if success:
                    # Also save to Redis for backward compatibility
                    await save_user_oauth_token(token_data)
                    # Store mapping from app user id to Slack user id
                    print("[Slack OAuth] Token data:", token_data)
                    slack_user_id = token_data.get("authed_user", {}).get("id")
                    print(f"[Slack OAuth] Slack user_id: {slack_user_id} for app user_id: {app_user_id}")
                    if app_user_id and slack_user_id:
                        await redis_client.set(f"app_to_slack_user:{app_user_id}", slack_user_id)
                        print(f"[Slack OAuth] Set mapping: app_to_slack_user:{app_user_id} -> {slack_user_id}")
                    else:
                        print(f"[Slack OAuth] Could not set mapping: app_user_id={app_user_id}, slack_user_id={slack_user_id}")
                    
                    # Redirect to frontend with success
                    return RedirectResponse(url=f"{FRONTEND_URL}/oauth/callback?success=true")
                else:
                    # Redirect to frontend with error
                    return RedirectResponse(url=f"{FRONTEND_URL}/oauth/callback?error=save_failed")
            else:
                print(f"[Slack OAuth] Token data: {token_data}")
                print(f"[Slack OAuth] REDIRECT_URI: {data.get('redirect_uri')}")
                print(f"[Slack OAuth] Error retrieving token: {token_data.get('error')}")
                # Redirect to frontend with error
                return RedirectResponse(url=f"{FRONTEND_URL}/oauth/callback?error=token_failed&message={token_data.get('error')}")
        
def get_slack_oauth_authorize_url(app_user_id=None):
    client_id = os.getenv("SLACK_CLIENT_ID")
    redirect_uri = os.getenv("SLACK_REDIRECT_URI")
    bot_scopes = "app_mentions:read,assistant:write,files:read,im:read"
    user_scopes = "channels:read,groups:read,im:read,mpim:read,users:read,im:history,groups:history,channels:history,search:read"
    url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={client_id}"
        f"&scope={bot_scopes}"
        f"&user_scope={user_scopes}"
        f"&redirect_uri={redirect_uri}"
    )
    if app_user_id:
        url += f"&state={app_user_id}"
    print(f"[Slack OAuth] get_slack_oauth_authorize_url: {url}")
    return url

async def get_slack_tokens_from_supabase(app_user_id: str):
    """Get Slack tokens from Supabase slack_integration table"""
    try:
        result = supabase.table("slack_integration").select("*").eq("user_id", app_user_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"[Slack OAuth] Error getting tokens from Supabase: {e}")
        return None

async def get_valid_user_access_token(slack_user_id: str, app_user_id: str | None = None) -> dict | None:
    if slack_user_id is None:
        raise ValueError("slack_user_id must not be None")
    
    # First try to get from Supabase if app_user_id is provided
    if app_user_id:
        supabase_tokens = await get_slack_tokens_from_supabase(app_user_id)
        if supabase_tokens:
            # Parse expires_at from ISO format string
            expires_at_str = supabase_tokens.get("expires_at")
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                    now = datetime.now()
                    if now < expires_at and supabase_tokens.get("user_access_token"):
                        print(f"[Slack OAuth] Valid token found in Supabase for app_user_id: {app_user_id}")
                        return {"access_token": supabase_tokens["user_access_token"]}
                    elif supabase_tokens.get("user_refresh_token"):
                        # Try to refresh the token
                        print(f"[Slack OAuth] Token expired, attempting refresh for app_user_id: {app_user_id}")
                        return await refresh_slack_token_from_supabase(supabase_tokens, app_user_id)
                except Exception as e:
                    print(f"[Slack OAuth] Error parsing expires_at: {e}")
    # Fallback to Redis
    token_json = await redis_client.get(f"slack_user_token:{slack_user_id}")
    if not token_json:
        print(f"[Slack OAuth] No token found in Redis for Slack user_id: {slack_user_id}")
        auth_url = get_slack_oauth_authorize_url(app_user_id or slack_user_id)
        print(f"[Slack OAuth] Returning auth_required with URL: {auth_url}")
        return {"auth_required": True, "auth_url": auth_url}
    token_info = json.loads(token_json)
    expires_at = token_info.get("expires_at", 0)
    now = int(time.time())
    # print(f"[Slack OAuth] Token info: {token_info}, now={now}, expires_at={expires_at}")
    if now < expires_at and token_info.get("user_access_token"):
        # print(f"[Slack OAuth] Token is valid, returning access_token")
        return {"access_token": token_info["user_access_token"]}
    print(f"[Slack OAuth] Access token expired for {slack_user_id}, refreshing...")
    refresh_token = token_info.get("refresh_token")
    if not refresh_token:
        print(f"[Slack OAuth] No refresh token for {slack_user_id}")
        auth_url = get_slack_oauth_authorize_url(app_user_id or slack_user_id)
        print(f"[Slack OAuth] Returning auth_required with URL: {auth_url}")
        return {"auth_required": True, "auth_url": auth_url}
    # Call Slack to refresh
    SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
    token_url = "https://slack.com/api/oauth.v2.access"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": SLACK_CLIENT_ID,
        "client_secret": SLACK_CLIENT_SECRET,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=data) as response:
            token_data = await response.json()
            print("[Slack OAuth] Refresh response:", token_data)
            if token_data.get("ok"):
                await save_user_oauth_token(token_data)
                print(f"[Slack OAuth] Refreshed and saved new token, returning access_token")
                return {"access_token": token_data.get("authed_user", {}).get("access_token")}
            else:
                print(f"[Slack OAuth] Failed to refresh token for {slack_user_id}: {token_data.get('error')}")
                auth_url = get_slack_oauth_authorize_url(app_user_id or slack_user_id)
                print(f"[Slack OAuth] Returning auth_required with URL: {auth_url}")
                return {"auth_required": True, "auth_url": auth_url, "error": token_data.get("error")}

async def refresh_slack_token_from_supabase(supabase_tokens, app_user_id):
    """Refresh Slack token using refresh token from Supabase"""
    refresh_token = supabase_tokens.get("user_refresh_token")
    if not refresh_token:
        print(f"[Slack OAuth] No refresh token in Supabase for app_user_id: {app_user_id}")
        auth_url = get_slack_oauth_authorize_url(app_user_id)
        return {"auth_required": True, "auth_url": auth_url}
    
    SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
    token_url = "https://slack.com/api/oauth.v2.access"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": SLACK_CLIENT_ID,
        "client_secret": SLACK_CLIENT_SECRET,
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=data) as response:
            token_data = await response.json()
            print("[Slack OAuth] Supabase refresh response:", token_data)
            if token_data.get("ok"):
                # Update Supabase with new tokens
                await save_user_oauth_token_to_supabase(token_data, app_user_id)
                print(f"[Slack OAuth] Refreshed and saved new token to Supabase for app_user_id: {app_user_id}")
                return {"access_token": token_data.get("authed_user", {}).get("access_token")}
            else:
                print(f"[Slack OAuth] Failed to refresh token from Supabase for {app_user_id}: {token_data.get('error')}")
                auth_url = get_slack_oauth_authorize_url(app_user_id)
                return {"auth_required": True, "auth_url": auth_url, "error": token_data.get("error")}