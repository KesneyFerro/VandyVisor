from typing import Optional
from enum import Enum
from pydantic import BaseModel


class CourseStatus(str, Enum):
    """Enum for course status in a study plan"""
    PLANNED = "planned"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    WAIVED = "waived"


class PlannedCourseBase(BaseModel):
    """Base class for planned course data"""
    course_id: int
    term_id: int
    status: CourseStatus = CourseStatus.PLANNED


class PlannedCourseCreate(PlannedCourseBase):
    """Schema for creating a new planned course"""
    pass


class PlannedCourseUpdate(BaseModel):
    """Schema for updating a planned course"""
    term_id: Optional[int] = None
    status: Optional[CourseStatus] = None


class PlannedCourseResponse(PlannedCourseBase):
    """Schema for planned course response"""
    id: int
    plan_id: int

    class Config:
        orm_mode = True
