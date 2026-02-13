import httpx
import asyncio
import subprocess
import json
import os
from typing import Dict, Any, List
import time

OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "phi3:mini"
INTENT_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "intend_classifiers.json")

_intent_context_cache = None

async def ensure_ollama_running():
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            await client.get(f"{OLLAMA_URL}/api/tags")
        # print("[phi3_intent] Ollama server is running.")
    except Exception:
        print("[phi3_intent] Ollama server not running. Attempting to start...")
        subprocess.Popen(["ollama", "serve"])  # Non-blocking
        await asyncio.sleep(2)
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                await client.get(f"{OLLAMA_URL}/api/tags")
            # print("[phi3_intent] Ollama server started successfully.")
        except Exception as e:
            print(f"[phi3_intent] ERROR: Ollama server could not be started or reached: {e}")
            raise RuntimeError("Ollama server could not be started or reached.") from e

def load_intent_registry_context() -> str:
    global _intent_context_cache
    if _intent_context_cache is not None:
        return _intent_context_cache
    with open(INTENT_REGISTRY_PATH, "r") as f:
        intents = json.load(f)
    context_lines = ["Here are the possible intents:"]
    for intent in intents:
        context_lines.append(f"- {intent['intent']}: {intent['description']}")
        if intent.get("example_prompts"):
            context_lines.append("  Examples:")
            for ex in intent["example_prompts"]:
                context_lines.append(f"    - {ex}")
    _intent_context_cache = "\n".join(context_lines)
    return _intent_context_cache

def build_few_shot_examples(intents: List[dict], n: int = 1) -> str:
    """Build few-shot examples from the first n example prompts for each intent."""
    lines = []
    for intent in intents:
        for ex in intent.get("example_prompts", [])[:n]:
            lines.append(f'User: "{ex}"')
            lines.append(json.dumps({
                "intent": intent["intent"],
                "reasoning": f"User intent: {intent['description']}"
            }))
    return "\n".join(lines)

async def classify_intent_with_phi3(prompt: str) -> Dict[str, Any]:
    # print(f"[phi3_intent] classify_intent_with_phi3 called with prompt: {prompt}")
    await ensure_ollama_running()
    with open(INTENT_REGISTRY_PATH, "r") as f:
        intents = json.load(f)
    context = load_intent_registry_context()
    few_shot = build_few_shot_examples(intents, n=1)
    full_prompt = (
        f"You are an intent classifier for a multi-provider assistant.\n\n"
        f"{context}\n\n"
        f"When given a user prompt, output only a single JSON object with the following fields:\n"
        f"- intent: one of [{', '.join([i['intent'] for i in intents])}]\n"
        f"- reasoning: a short explanation\n\n"
        f"Do not output anything except the JSON object. Do not explain, apologize, or add any extra text.\n\n"
        f"{few_shot}\n\n"
        f"User: \"{prompt}\""
    )
    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": True
    }
    # print(f"[phi3_intent] Sending prompt to Ollama (length: {len(full_prompt)} chars)")
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/generate", json=payload) as response:
                full_response = ""
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        full_response += chunk
                    except Exception as e:
                        print(f"[phi3_intent] ERROR: Failed to parse stream chunk: {e}")
                elapsed = time.time() - start_time
                print(f"[phi3_intent] Ollama response time: {elapsed:.2f} seconds")
                # print(f"[phi3_intent] Full response from Ollama (truncated): {full_response[:200]}...")
                json_start = full_response.find('{')
                json_end = full_response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = full_response[json_start:json_end]
                    try:
                        parsed = json.loads(json_str)
                        print(f"[phi3_intent] Parsed JSON: {parsed}")
                        return {
                            "intent": parsed.get("intent", "ambiguous"),
                            "reasoning": parsed.get("reasoning", "")
                        }
                    except Exception as e:
                        print(f"[phi3_intent] ERROR: Failed to parse JSON: {e}")
                print("[phi3_intent] Fallback: Could not parse LLM response as JSON.")
                return {"intent": "ambiguous", "reasoning": "Could not parse LLM response"}
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[phi3_intent] Ollama response time (error): {elapsed:.2f} seconds")
        print(f"[phi3_intent] ERROR: LLM call failed: {e}")
        return {"intent": "ambiguous", "reasoning": f"LLM call failed: {e}"} 