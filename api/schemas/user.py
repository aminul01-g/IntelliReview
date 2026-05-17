from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v) > 72:
            raise ValueError('Password must be 72 bytes or fewer')
        return v

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v) > 72:
            raise ValueError('Password must be 72 bytes or fewer')
        return v

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
