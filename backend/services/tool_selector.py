from services.registry import get_providers_from_registry

async def detect_providers(prompt: str) -> list[str]:
    providers = await get_providers_from_registry()
    prompt_lower = prompt.lower()
    detected = [provider for provider in providers if provider in prompt_lower]
    return detected