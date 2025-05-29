from datetime import datetime, UTC
from beanie import Document
from pydantic import EmailStr, Field

class User(Document):
    user_id: int
    user_type: str # "user" or "admin"
    email: EmailStr
    username: str
    hashed_password: str

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    class Settings:
        collection = "users"
