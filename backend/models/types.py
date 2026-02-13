from pydantic import BaseModel
from typing import Dict, Any

class UserPrompt(BaseModel):
    prompt: str
    user_id: str


#Might need deleting later
class ToolCall(BaseModel):
    name: str
    parameters: Dict[str, Any]