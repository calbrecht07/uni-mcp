from services.cache import redis_client
from supabase import create_client
import os
import json
from datetime import datetime

SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_PROJECT_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials are missing")

supabase = create_client(SUPABASE_PROJECT_URL, SUPABASE_KEY)

async def get_integration_status(user_id: str) -> dict:
    status = {}
    # Slack integration
    try:
        slack_result = supabase.table("slack_integration").select("*").eq("user_id", user_id).execute()
        slack_data = slack_result.data[0] if slack_result.data else None
        if slack_data:
            slack_user_id = slack_data.get("slack_user_id")
            # Check Redis for token validity
            token_json = await redis_client.get(f"slack_user_token:{slack_user_id}")
            token_info = json.loads(token_json) if token_json else None
            expires_at = token_info.get("expires_at") if token_info else None
            valid = False
            if expires_at:
                try:
                    valid = int(expires_at) > int(datetime.now().timestamp())
                except Exception:
                    valid = False
            status["slack"] = {
                "connected": True,
                "slack_user_id": slack_user_id,
                "scopes": slack_data.get("scope"),
                "token_valid": valid,
                "token_expires_at": expires_at,
            }
        else:
            status["slack"] = {"connected": False}
    except Exception as e:
        status["slack"] = {"connected": False, "error": str(e)}

    # Notion integration (if you have a notion_integration table)
    try:
        notion_result = supabase.table("notion_integration").select("*").eq("user_id", user_id).execute()
        notion_data = notion_result.data[0] if notion_result.data else None
        if notion_data:
            # If you cache Notion tokens in Redis, check validity here
            # For now, just report connection
            status["notion"] = {
                "connected": True,
                "notion_user_id": notion_data.get("notion_user_id"),
                "scopes": notion_data.get("scope"),
            }
        else:
            status["notion"] = {"connected": False}
    except Exception as e:
        status["notion"] = {"connected": False, "error": str(e)}

    return status 