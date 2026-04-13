from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth import get_current_user
from app.db.session import get_async_db
from app.models import User, StudyPlan, PlannedCourse
from app.schemas.study_plan import StudyPlanCreate, StudyPlanResponse, StudyPlanUpdate
from app.schemas.planned_course import PlannedCourseCreate, PlannedCourseResponse

router = APIRouter()


@router.post("/", response_model=StudyPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_study_plan(
    plan_data: StudyPlanCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new study plan.
    """
    plan = StudyPlan(
        name=plan_data.name,
        description=plan_data.description,
        user_id=current_user.id,
        primary=plan_data.primary
    )
    
    # If this is set as primary, unset any other primary plans
    if plan_data.primary:
        stmt = select(StudyPlan).where(
            StudyPlan.user_id == current_user.id,
            StudyPlan.primary == True
        )
        result = await db.execute(stmt)
        other_primary_plans = result.scalars().all()
        
        for other_plan in other_primary_plans:
            other_plan.primary = False
    
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    
    return plan


@router.get("/", response_model=List[StudyPlanResponse])
async def get_study_plans(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all study plans for the current user.
    """
    stmt = select(StudyPlan).where(StudyPlan.user_id == current_user.id)
    result = await db.execute(stmt)
    plans = result.scalars().all()
    
    return plans


@router.get("/{plan_id}", response_model=StudyPlanResponse)
async def get_study_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific study plan.
    """
    stmt = select(StudyPlan).where(
        StudyPlan.id == plan_id,
        StudyPlan.user_id == current_user.id
    )
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study plan not found"
        )
    
    return plan


@router.put("/{plan_id}", response_model=StudyPlanResponse)
async def update_study_plan(
    plan_id: int,
    plan_data: StudyPlanUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a study plan.
    """
    stmt = select(StudyPlan).where(
        StudyPlan.id == plan_id,
        StudyPlan.user_id == current_user.id
    )
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study plan not found"
        )
    
    # Update plan fields
    for field, value in plan_data.dict(exclude_unset=True).items():
        setattr(plan, field, value)
    
    # If setting as primary, unset other primary plans
    if plan_data.primary:
        stmt = select(StudyPlan).where(
            StudyPlan.user_id == current_user.id,
            StudyPlan.id != plan_id,
            StudyPlan.primary == True
        )
        result = await db.execute(stmt)
        other_primary_plans = result.scalars().all()
        
        for other_plan in other_primary_plans:
            other_plan.primary = False
    
    await db.commit()
    await db.refresh(plan)
    
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_study_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a study plan.
    """
    stmt = select(StudyPlan).where(
        StudyPlan.id == plan_id,
        StudyPlan.user_id == current_user.id
    )
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study plan not found"
        )
    
    await db.delete(plan)
    await db.commit()
    
    return None


@router.post("/{plan_id}/courses", response_model=PlannedCourseResponse)
async def add_course_to_plan(
    plan_id: int,
    course_data: PlannedCourseCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a course to a study plan.
    """
    # Verify plan exists and belongs to user
    stmt = select(StudyPlan).where(
        StudyPlan.id == plan_id,
        StudyPlan.user_id == current_user.id
    )
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study plan not found"
        )
    
    # Create the planned course
    planned_course = PlannedCourse(
        plan_id=plan_id,
        course_id=course_data.course_id,
        term_id=course_data.term_id,
        status=course_data.status
    )
    
    db.add(planned_course)
    await db.commit()
    await db.refresh(planned_course)
    
    return planned_course


@router.get("/{plan_id}/courses", response_model=List[PlannedCourseResponse])
async def get_plan_courses(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all courses in a study plan.
    """
    # Verify plan exists and belongs to user
    stmt = select(StudyPlan).where(
        StudyPlan.id == plan_id,
        StudyPlan.user_id == current_user.id
    )
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study plan not found"
        )
    
    # Get planned courses
    stmt = select(PlannedCourse).where(PlannedCourse.plan_id == plan_id)
    result = await db.execute(stmt)
    planned_courses = result.scalars().all()
    
    return planned_courses
