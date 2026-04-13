from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class StudyPlanBase(BaseModel):
    """Base class for study plan data"""
    name: str
    description: Optional[str] = None
    primary: bool = False


class StudyPlanCreate(StudyPlanBase):
    """Schema for creating a new study plan"""
    pass


class StudyPlanUpdate(BaseModel):
    """Schema for updating a study plan"""
    name: Optional[str] = None
    description: Optional[str] = None
    primary: Optional[bool] = None


class StudyPlanResponse(StudyPlanBase):
    """Schema for study plan response"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
