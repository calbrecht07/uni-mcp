from services.llm.llm_base import LLMClient
import json
import traceback
import openai
import os
import re
from typing import List, Union, cast, Iterable
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from models.types import UserPrompt, ToolCall

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Helper to clean and format Slack output

def clean_slack_output(text):
    # Remove excessive stars, hashtags, and markdown headers
    text = re.sub(r"[#*]{2,}", "", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    # Convert markdown links to Slack format: [text](url) -> <url|text>
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", text)
    # Remove image markdown: ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

class OpenAIChatLLM(LLMClient):
    def __init__(self, model="gpt-3.5-turbo"):
        self.model = model

    async def simple_completion(self, prompt: str) -> str:
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": "You are a helpful, friendly assistant."},
            {"role": "user", "content": prompt}
        ]
        try:
            response = await client.chat.completions.create(  # type: ignore
                model=self.model,
                messages=messages,
                temperature=0.3,
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except Exception as e:
            print("[OpenAIChatLLM] Error in simple_completion:", e)
            traceback.print_exc()
            return "(Sorry, I couldn't process your request.)"

    async def call(self, prompt: UserPrompt, tools: List[dict]) -> List[ToolCall]:
        system_content = (
            "You are a helpful assistant."  
            "Follow the tool structure and parameter schema exactly as defined in the tool manifest."  
            "If a parameter (e.g., 'query') requires a single word, do not use a sentence."  
            "Respect any specified format in tool descriptions or parameter schemas."  
            "If the user's request is unclear, ask a clarifying question before continuing."  
            "When returning a link (e.g., a Notion page), offer to summarize its content."  
            "If the user mentions a conversation or thread, offer to summarize it."  
            "Make the conversation helpful and interactive."  
            "Always offer a follow-up, like 'Would you like a summary of this page?' or 'Is there anything else I can help with?'"  
            "Format output for Slack: use Slack hyperlinks (<url|text>), avoid excessive markdown, and keep it clean."
        )
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt.prompt}
        ]
        # Do not type-annotate tools_param, as it is a list of dicts from the registry
        tools_param = tools if tools else None
        try:
            if tools_param:
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    tools=cast(Iterable[ChatCompletionToolParam], tools_param),
                    tool_choice="auto",
                    temperature=0.3,
                )
            else:
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.3,
                )
            tool_calls = []
            for choice in response.choices:
                if choice.message.tool_calls:
                    for tool_call in choice.message.tool_calls:
                        # Parse arguments as dict if needed
                        args = tool_call.function.arguments
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                args = {}
                        tool_calls.append(ToolCall(
                            name=tool_call.function.name,
                            parameters=args or {}
                        ))
            return tool_calls
        except Exception as e:
            print("[OpenAIChatLLM] Error in call:", e)
            traceback.print_exc()
            return []

    async def finalize(self, prompt: UserPrompt, tool_calls: List[ToolCall], tool_results: List, **kwargs) -> str:
        try:
            # If there are tool results, ask the LLM to summarize and format them for Slack
            if tool_results:
                system_content = (
                    "You are a helpful assistant. Summarize and format the following tool results for a Slack user. "
                    "If the user's request is ambiguous or lacks context, ask a clarifying question before proceeding. "
                    "If you return a link (e.g., to a Notion page), offer to summarize its content. "
                    "If the user references a conversation or thread, offer to summarize it. "
                    "Always strive to make the conversation as helpful and interactive as possible. "
                    "Always offer a follow-up question, such as 'Would you like a summary of this page?' or 'Is there anything else I can help with?'. "
                    "Format your output for Slack: use Slack hyperlinks (<url|text>), avoid excessive stars, hashtags, or markdown headers, and keep formatting clean."
                )
                messages: List[ChatCompletionMessageParam] = [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt.prompt},
                    {"role": "assistant", "content": f"Tool results: {json.dumps(tool_results, ensure_ascii=False)}"}
                ]
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.3,
                )
                content = response.choices[0].message.content
                if content:
                    # Remove common unwanted unicode and ASCII art
                    content = re.sub(r"[•◆◇○●■□▲▼▶◀★☆→←↑↓※§¤†‡•¶¤§©®™✓✔✗✘☑☒☓☠☢☣☤☥☦☧☨☩☪☫☬☭☮☯☸☹☺☻☼☽☾♠♣♥♦♪♫♭♯⚡☀☁☂☃☄★☆]+", "", content)
                    content = re.sub(r"[\u2500-\u25FF]+", "", content)  # Box drawing, block, geometric shapes
                    content = re.sub(r"[\u2700-\u27BF]+", "", content)  # Dingbats
                    content = content.replace('```', '')  # Remove code block markers if not needed
                    return clean_slack_output(content)
            # Fallback: join tool results as string
            final_message = "\n\n".join(str(r) for r in tool_results if r)
            if final_message:
                final_message = re.sub(r"[•◆◇○●■□▲▼▶◀★☆→←↑↓※§¤†‡•¶¤§©®™✓✔✗✘☑☒☓☠☢☣☤☥☦☧☨☩☪☫☬☭☮☯☸☹☺☻☼☽☾♠♣♥♦♪♫♭♯⚡☀☁☂☃☄★☆]+", "", final_message)
                final_message = re.sub(r"[\u2500-\u25FF]+", "", final_message)
                final_message = re.sub(r"[\u2700-\u27BF]+", "", final_message)
                final_message = final_message.replace('```', '')
            return clean_slack_output(final_message)
        except Exception as e:
            print("[OpenAIChatLLM] Error in finalize:", e)
            traceback.print_exc()
            return "(Sorry, there was an error formatting the response.)"