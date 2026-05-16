from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    role: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


class TokenPayload(BaseModel):
    """Token payload for JWT."""
    sub: str
    username: str
    role: Optional[str] = None
    team_id: Optional[int] = None
    exp: datetime
