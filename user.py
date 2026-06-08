from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    telegram_id: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    status: Optional[str] = "pending"
    role: Optional[str] = "user"
    approved_by: Optional[int] = None
    last_action: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True
