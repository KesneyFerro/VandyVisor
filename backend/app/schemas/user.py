from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    """Base class for user data"""
    email: EmailStr
    full_name: str
    year: Optional[int] = None
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    year: Optional[int] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: int

    class Config:
        orm_mode = True
