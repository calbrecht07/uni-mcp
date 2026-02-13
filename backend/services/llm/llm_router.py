import re
from .phi3_intent import classify_intent_with_phi3

# Heuristic intent detection
# Returns: 'chat_smalltalk', 'ambiguous', 'search_data', 'summarize', or 'other'
def detect_intent(text: str) -> str:
    text = text.strip().lower()
    if not text:
        return 'ambiguous'
    # System status intent
    system_keywords = [
        'connected', 'scopes', 'authorize', 'linked', 'integration', 'status',
        'which tools', 'what integrations', 'what providers', 'what is connected',
        'are you linked', 'is notion connected', 'is slack connected', 'active integrations', 'available integrations', 'my integrations', 'show integrations', 'list integrations', 'show connections', 'list connections', 'what can you access', 'what can you do', 'permissions', 'access', 'auth', 'authorizations', 'what accounts', 'which accounts', 'which services', 'what services', 'what apps', 'which apps', 'what bots', 'which bots'
    ]
    for kw in system_keywords:
        if kw in text:
            return 'system_status'
    # Smalltalk/greeting
    if text in ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']:
        return 'chat_smalltalk'
    # Summarize intent
    if 'summarize' in text or 'summary' in text:
        return 'summarize'
    # Question/command
    if text.endswith('?') or re.match(r'^(who|what|when|where|why|how|can|should|does|do|pull|give|bring|is|are|could|would|will|did|please)\b', text):
        return 'search_data'
    # If it's a short phrase or ambiguous
    if len(text.split()) < 3:
        return 'ambiguous'
    # Default: treat as ambiguous
    return 'ambiguous'

# Intent router
# Returns: intent type string
async def route_intent(text: str) -> str:
    return detect_intent(text)

# LLM-based intent router using phi3:mini
async def route_intent_phi3(text: str) -> str:
    result = await classify_intent_with_phi3(text)
    return result.get("intent", "ambiguous")