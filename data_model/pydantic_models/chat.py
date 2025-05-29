from pydantic import BaseModel
from datetime import datetime
from typing import List

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    session_id: str

class MessageResponse(BaseModel):
    content: str
    role: str
    timestamp: datetime

class SessionResponse(BaseModel):
    session_id: str
    messages: List[MessageResponse]
    created_at: datetime
    updated_at: datetime 