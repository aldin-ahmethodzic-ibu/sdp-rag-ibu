from datetime import datetime, timezone
from beanie import Document
from pydantic import EmailStr, Field

class User(Document):
    user_id: int
    user_type: str # "user" or "admin"
    email: EmailStr
    username: str
    hashed_password: str

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        collection = "users"
