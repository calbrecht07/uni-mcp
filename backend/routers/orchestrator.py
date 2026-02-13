from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from models.types import UserPrompt
from models.types import ToolCall
from services.tool_router import handle_tool_call
from services.tool_selector import detect_providers
from services.registry import build_tool_manifest, get_primary_search_tools
from services.llm.openai_llm import OpenAIChatLLM
from providers.slack.slack_oauth import get_slack_oauth_authorize_url
from services.cache import redis_client
import time
import asyncio
from pydantic import BaseModel
from typing import Optional
from services.chat_history import save_message, get_history
from services.llm.llm_router import route_intent
import datetime
from services.llm.phi3_intent import classify_intent_with_phi3
import re
from providers.jira.jira_utils import prompt_to_jql, prompt_to_jql_phi3

router = APIRouter()

@router.post("/prompt")
async def handle_prompt(request: UserPrompt):
    start = time.time()
    # 0. Intent detection using phi3
    phi3_result = await classify_intent_with_phi3(request.prompt)
    if not isinstance(phi3_result, dict):
        phi3_result = {"intent": "ambiguous", "reasoning": "Non-dict result from phi3"}
    intent = phi3_result.get("intent", "ambiguous")
    reasoning = phi3_result.get("reasoning", "")
    print(f"[Intent Router] Detected intent: {intent} | Reasoning: {reasoning}")

    if intent == 'smalltalk':
        return {"message": "Hi! How can I help you today?"}
    if intent == 'ambiguous':
        llm = OpenAIChatLLM(model="gpt-3.5-turbo")
        clarifying_prompt = (
            "A user sent the following message to a chatbot: '" + request.prompt + "'. "
            "Reply with a friendly, engaging clarifying question or ask for more details. "
            "Do not answer the question, just ask for clarification."
        )
        clarifying_response = await llm.simple_completion(clarifying_prompt)
        return {"message": clarifying_response}
    if intent == 'summarize':
        return {"message": "Sure! Please specify what you'd like summarized (e.g., the current conversation, a document, etc.)."}
    if intent == 'system_status':
        from services.llm.system_status import get_integration_status
        status = await get_integration_status(request.user_id)
        return {"system_status": status}
    # Only proceed to LLM/tool calls for actionable intents

    providers = await detect_providers(request.prompt)
    if not providers:
        providers = []
    llm = OpenAIChatLLM()

    # 1. If providers are specified, use only those tools
    print(f"[Orchestrator] Calling build_tool_manifest for user_id={request.user_id}, providers={providers}")
    if providers:
        tools = await build_tool_manifest(request.user_id, providers)
        print(f"[Orchestrator] build_tool_manifest returned {len(tools)} tools (with providers)")
        print(f"[Orchestrator] tools: {tools}")
        print(f"Detected providers: {providers}")
    else:
        tools = await get_primary_search_tools(request.user_id)
        print(f"[Orchestrator] build_tool_manifest not called, using get_primary_search_tools")
        print("No specific providers detected, using primary search tools.")

    mid1 = time.time()

    # 2. Let LLM select tools (if any)
    print("Tools being sent to LLM:", [tool["function"]["name"] for tool in tools])
    tool_calls_raw = await llm.call(request, tools)
    # print(f"Tool calls raw: {tool_calls_raw}")

    # Convert dicts to ToolCall objects if needed
    tool_calls = []
    if tool_calls_raw and isinstance(tool_calls_raw[0], dict):
        tool_calls = [
            ToolCall(
                name=call["function"]["name"],
                parameters=call.get("parameters") or {}
            )
            for call in tool_calls_raw
        ]
    else:
        tool_calls = tool_calls_raw or []

    # 3. If no providers detected, ensure all primary search tools are present
    if not providers:
        primary_tools = await get_primary_search_tools(request.user_id)
        primary_tool_names = {tool["function"]["name"] for tool in primary_tools}
        tool_call_names = {call.name for call in tool_calls}
        missing_primary_tools = primary_tool_names - tool_call_names
        if missing_primary_tools:
            print(f"Adding missing primary tools: {missing_primary_tools}")
            for tool in primary_tools:
                if tool["function"]["name"] in missing_primary_tools:
                    tool_calls.append(
                        ToolCall(
                            name=tool["function"]["name"],
                            parameters={"query": request.prompt}
                        )
                    )

    # 4. If no tool calls at all, fallback to all primary search tools
    if not tool_calls:
        print("No tool calls from LLM – falling back to primary search tools")
        primary_tools = await get_primary_search_tools(request.user_id)
        tool_calls = [
            ToolCall(
                name=tool["function"]["name"],
                parameters={"query": request.prompt}
            )
            for tool in primary_tools
        ]

    mid2 = time.time()

    # 5. Prepare and run tool calls in parallel
    async def prepare_and_call(call):
        params = call.parameters.copy()
        if call.name.startswith("slack_"):
            slack_user_id = await redis_client.get(f"app_to_slack_user:{request.user_id}")
            print(f"[Orchestrator] Mapped app user_id {request.user_id} to Slack user_id: {slack_user_id}")
            if not slack_user_id:
                print("[Orchestrator] No Slack user_id mapping found. User must authorize Slack.")
                return {
                    "error": "slack_auth_required",
                    "auth_url": get_slack_oauth_authorize_url(request.user_id),
                    "message": "User must authorize Slack before this action can be performed."
                }
            params["slack_user_id"] = slack_user_id
            params["app_user_id"] = request.user_id
        # Inject the correct search parameter for each tool
        if call.name == "jira_search_issues":
            if "jql" not in params:
                params["jql"] = prompt_to_jql(request.prompt)
                # params["jql"] = prompt_to_jql_phi3(request.prompt)
            # Always pass user_id for Jira tools, never hardcode cloud_id
            params["user_id"] = request.user_id
        elif call.name.startswith("jira_"):
            # For all other Jira tools, always pass user_id
            params["user_id"] = request.user_id
        elif "query" not in params:
            print(f"[Orchestrator] Missing 'query' in params for tool {call.name}, injecting default prompt.")
            params["query"] = request.prompt
        return await handle_tool_call(ToolCall(name=call.name, parameters=params))

    print("Tools being used for this request:", [call.name for call in tool_calls])
    tool_results = await asyncio.gather(*[prepare_and_call(call) for call in tool_calls])

    mid3 = time.time()

    # --- Structured MCP response for 'search_data' intent ---
    if intent == 'search_data':
        notion_matches = []
        slack_matches = []
        query = request.prompt
        notion_seen = set()
        slack_seen = set()
        for result in tool_results:
            if not isinstance(result, dict):
                continue
            # Slack: extract from messages.matches
            if 'messages' in result and isinstance(result['messages'], dict):
                for match in result['messages'].get('matches', []):
                    if not isinstance(match, dict):
                        continue
                    # Filter out messages from 'uni-app'
                    user = match.get('username') or match.get('user') or ''
                    if user == 'uni-app':
                        continue
                    slack_permalink = match.get('permalink') or match.get('url')
                    text = match.get('text') or ''
                    channel_type = 'Direct Message' if match.get('type') == 'im' else match.get('type', '')
                    # Deduplicate by permalink + text
                    slack_key = f"{slack_permalink}:{text}"
                    if slack_permalink and slack_key not in slack_seen:
                        slack_seen.add(slack_key)
                        slack_matches.append({
                            "text": text,
                            "user": user,
                            "channel_type": channel_type,
                            "slack_permalink": slack_permalink
                        })
            # Notion: extract from results
            elif 'results' in result and isinstance(result['results'], list):
                for notion_item in result['results']:
                    if not isinstance(notion_item, dict):
                        continue
                    permalink = notion_item.get('url')
                    # Extract title from properties
                    title = 'Notion Page'
                    properties = notion_item.get('properties', {})
                    for prop in properties.values():
                        if prop.get('type') == 'title' and prop.get('title'):
                            title = ''.join([t.get('plain_text', '') for t in prop['title']]) or title
                            break
                    # Format last_edited
                    last_edited_raw = notion_item.get('last_edited_time', '')
                    last_edited = ''
                    if last_edited_raw:
                        try:
                            dt = datetime.datetime.fromisoformat(last_edited_raw.replace('Z', '+00:00'))
                            last_edited = dt.strftime('%d %B %Y')
                        except Exception:
                            last_edited = last_edited_raw
                    # Extract status from properties
                    status = ''
                    for prop in properties.values():
                        if prop.get('type') == 'status' and prop.get('status'):
                            status = prop['status'].get('name', '')
                            break
                    summary = 'Fetching...'
                    # Deduplicate by permalink
                    if permalink and permalink not in notion_seen:
                        notion_seen.add(permalink)
                        notion_matches.append({
                            "title": title,
                            "permalink": permalink,
                            "summary": summary,
                            "last_edited": last_edited,
                            "status": status
                        })
        match_count = len(notion_matches) + len(slack_matches)
        if match_count == 0:
            return {"message": "Sorry, I couldn't find any information in Slack or Notion."}
        final_json = {
            "query": query,
            "match_count": match_count,
            "notion_matches": notion_matches,
            "slack_matches": slack_matches
        }
        print("\n--- [Orchestrator] ---", flush=True)
        print("[DEBUG] Final MCP JSON sent to frontend:", final_json, flush=True)
        return final_json

    # --- End MCP response ---

    final_response = await llm.finalize(request, tool_calls, tool_results)
    end = time.time()

    print(f"TIMING: tools={mid1-start:.2f}s, llm_call={mid2-mid1:.2f}s, tool_result={mid3-mid2:.2f}s, finalize={end-mid3:.2f}s, total={end-start:.2f}s")
    return { "message": final_response }

class ChatMessage(BaseModel):
    user_id: str
    message: str
    sender: str
    session_id: Optional[str] = None

@router.post("/chat/history")
async def save_chat_message(msg: ChatMessage):
    """
    Save a chat message to Supabase chat_history table.
    """
    if not msg.session_id:
        return JSONResponse(content={"error": "session_id is required for all chat messages."}, status_code=400)
    result = await save_message(msg.user_id, msg.message, msg.sender, msg.session_id)
    return JSONResponse(content=result)

@router.get("/chat/history")
async def get_chat_history(user_id: str, session_id: Optional[str] = None):
    """
    Retrieve chat history for a user (and optional session).
    """
    result = await get_history(user_id, session_id)
    return JSONResponse(content=result)
