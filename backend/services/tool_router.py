import os
from services.cache import redis_client
import json
from models.types import ToolCall
from services.registry import get_context_registry_cached, get_tool_handler_mapping

CACHE_EXPIRATION = 300  # in seconds

async def handle_tool_call(tool_call: ToolCall) -> dict:
    """
    Routes a tool call to the correct context provider function with caching, using the dynamic registry.
    """
    name = tool_call.name
    params = tool_call.parameters

    # Fetch the dynamic registry and handler mapping
    registry = await get_context_registry_cached()
    handler_map = get_tool_handler_mapping()
    tool_entry = next((entry for entry in registry if entry.get("name") == name), None)
    if not tool_entry:
        return {"error": f"Unsupported tool name: {name}"}
    handler = handler_map.get(name)
    if not handler:
        return {"error": f"No handler function found for tool: {name}"}

    # Use default cache_key logic (always a string)
    cache_key = f"tool_call:{name}:{json.dumps(params, sort_keys=True)}"

    print(f"[Tool Router] Handling tool call: {name} with parameters: {params}")
    cached_result = await redis_client.get(cache_key)
    if cached_result:
        print(f"[Tool Router] Returning cached result for {name} (cache_key={cache_key})")
        return json.loads(cached_result)

    result = await handler(params)
    # Only cache if result is not empty and not an error
    is_empty = False
    is_error = False
    if result is None:
        is_empty = True
    elif isinstance(result, str) and not result.strip():
        is_empty = True
    elif isinstance(result, dict):
        if not any(result.values()):
            is_empty = True
        if 'error' in result:
            is_error = True
    if not is_empty and not is_error:
        await redis_client.setex(cache_key, CACHE_EXPIRATION, json.dumps(result))
        print(f"[Tool Router] Cached API result for {name} (cache_key={cache_key})")
    else:
        print(f"[Tool Router] Did NOT cache empty or error API result for {name} (cache_key={cache_key})")
    # Always return a dict
    if not isinstance(result, dict):
        return {"result": result}
    return result