import os
from supabase import create_client
from typing import Optional, List, Dict

SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_PROJECT_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials are missing")

supabase = create_client(SUPABASE_PROJECT_URL, SUPABASE_KEY)

async def save_message(user_id: str, message: str, sender: str, session_id: Optional[str] = None) -> Dict:
    data = {
        "user_id": user_id,
        "message": message,
        "sender": sender,
    }
    if session_id:
        data["session_id"] = session_id
    response = supabase.table("chat_history").insert(data).execute()
    return response.data[0] if response.data else {}

async def get_history(user_id: str, session_id: Optional[str] = None) -> List[Dict]:
    query = supabase.table("chat_history").select("*").eq("user_id", user_id)
    if session_id:
        query = query.eq("session_id", session_id)
    query = query.order("created_at", desc=False)
    response = query.execute()
    return response.data or [] 