from abc import ABC, abstractmethod
from models.types import ToolCall, UserPrompt

class LLMClient(ABC):
    @abstractmethod
    def call(self, prompt: UserPrompt, tools: list[dict]) -> ToolCall:
        pass