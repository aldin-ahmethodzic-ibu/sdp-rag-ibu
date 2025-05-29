from datetime import datetime, timezone
from typing import List

from beanie import Document
from pydantic import Field, BaseModel

class Message(BaseModel):
    content: str
    role: str  # "user" or "assistant"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Session(Document):
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        collection = "sessions"