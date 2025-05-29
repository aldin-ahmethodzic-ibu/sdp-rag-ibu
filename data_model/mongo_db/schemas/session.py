from datetime import datetime, UTC
from typing import List

from beanie import Document
from pydantic import Field

class Message(Document):
    content: str
    role: str  # "user" or "assistant"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class Session(Document):
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        collection = "sessions"