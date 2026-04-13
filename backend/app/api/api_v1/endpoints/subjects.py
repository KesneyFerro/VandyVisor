from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.models import Subject, Course

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_subjects(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get a list of all subjects.
    """
    subjects = await db.query(Subject).all()
    
    return [
        {
            "id": subject.id,
            "subject_code": subject.subject_code,
            "name": subject.name,
            "department": subject.department,
            "school": subject.school
        }
        for subject in subjects
    ]


@router.get("/{subject_code}", response_model=dict)
async def get_subject(
    subject_code: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get detailed information about a specific subject.
    """
    subject = await db.query(Subject).filter(Subject.subject_code == subject_code).first()
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    return {
        "id": subject.id,
        "subject_code": subject.subject_code,
        "name": subject.name,
        "department": subject.department,
        "school": subject.school
    }


@router.get("/{subject_code}/courses", response_model=List[dict])
async def get_subject_courses(
    subject_code: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get all courses for a specific subject.
    """
    courses = await db.query(Course).filter(Course.subject_code == subject_code).all()
    
    return [
        {
            "id": course.id,
            "subject_code": course.subject_code,
            "catalog_number": course.catalog_number,
            "title": course.title,
            "level": course.level,
            "credits": float(course.units_earned)
        }
        for course in courses
    ]
