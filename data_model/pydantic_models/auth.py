from typing import Optional
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    user_id: int
    user_type: str
    email: str
    username: str
    disabled: Optional[bool] = None

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    user_type: str = "user"