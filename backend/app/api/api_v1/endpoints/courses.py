from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.models import Course, Subject
from app.services.course_eligibility import get_user_eligible_courses
from app.core.auth import get_current_active_user

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_courses(
    subject: Optional[str] = None,
    level: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get a list of courses with optional filtering.
    """
    query = db.query(Course)
    
    if subject:
        query = query.filter(Course.subject_code == subject)
    
    if level:
        query = query.filter(Course.level == level)
    
    if search:
        query = query.filter(
            Course.title.ilike(f"%{search}%") | 
            Course.description.ilike(f"%{search}%")
        )
    
    courses = await query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": course.id,
            "subject_code": course.subject_code,
            "catalog_number": course.catalog_number,
            "title": course.title,
            "level": course.level,
            "credits": float(course.units_earned),
            "description": course.description
        }
        for course in courses
    ]


@router.get("/{course_id}", response_model=dict)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get detailed information about a specific course.
    """
    course = await db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Get prerequisites
    prereqs = await db.execute("""
        SELECT rg.id, rg.logic, rg.min_count
        FROM requisite_groups rg
        WHERE rg.course_id = :course_id AND rg.kind = 'pre'
    """, {"course_id": course_id})
    
    prereq_groups = []
    for prereq_group in prereqs:
        members = await db.execute("""
            SELECT rgm.id, rgm.target_course_id, rgm.target_subject, rgm.target_catalog,
                c.subject_code, c.catalog_number, c.title
            FROM requisite_group_members rgm
            LEFT JOIN courses c ON rgm.target_course_id = c.id
            WHERE rgm.group_id = :group_id
        """, {"group_id": prereq_group.id})
        
        group_members = []
        for member in members:
            if member.target_course_id:
                group_members.append({
                    "course_id": member.target_course_id,
                    "subject_code": member.subject_code,
                    "catalog_number": member.catalog_number,
                    "title": member.title
                })
            else:
                group_members.append({
                    "subject_code": member.target_subject,
                    "catalog_number": member.target_catalog
                })
        
        prereq_groups.append({
            "logic": prereq_group.logic,
            "min_count": prereq_group.min_count,
            "members": group_members
        })
    
    return {
        "id": course.id,
        "subject_code": course.subject_code,
        "catalog_number": course.catalog_number,
        "title": course.title,
        "description": course.description,
        "level": course.level,
        "credits": float(course.units_earned),
        "is_offered_fall": course.is_offered_fall,
        "is_offered_spring": course.is_offered_spring,
        "is_offered_summer": course.is_offered_summer,
        "prerequisites": prereq_groups,
        "prerequisites_raw": course.prerequisites_raw,
        "corequisites_raw": course.corequisites_raw,
        "antirequisites_raw": course.antirequisites_raw
    }


@router.get("/eligible/{user_id}", response_model=List[dict])
async def get_eligible_courses(
    user_id: int,
    term_code: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get a list of courses that a user is eligible to take.
    """
    # Authorization check (users can only see their own data or admins can see all)
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access this user's data")
    
    eligible_courses = await get_user_eligible_courses(db, user_id, term_code)
    
    return [
        {
            "id": course.id,
            "subject_code": course.subject_code,
            "catalog_number": course.catalog_number,
            "title": course.title,
            "level": course.level,
            "credits": float(course.units_earned)
        }
        for course in eligible_courses
    ]
