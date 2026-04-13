from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_async_db
from app.models import User
from app.services.course_recommendations import recommend_courses

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_recommendations(
    plan_id: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get course recommendations for the current user.
    
    Args:
        plan_id: Optional ID of a study plan to base recommendations on
        limit: Maximum number of recommendations to return
    """
    recommendations = await recommend_courses(
        user_id=current_user.id,
        plan_id=plan_id,
        limit=limit,
        db=db
    )
    
    return recommendations


@router.get("/interests", response_model=List[dict])
async def get_interest_based_recommendations(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get course recommendations based on user interests.
    
    Args:
        limit: Maximum number of recommendations to return
    """
    recommendations = await recommend_courses(
        user_id=current_user.id,
        interest_based=True,
        limit=limit,
        db=db
    )
    
    return recommendations


@router.get("/degree", response_model=List[dict])
async def get_degree_requirements_recommendations(
    program_id: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get course recommendations based on degree requirements.
    
    Args:
        program_id: Optional program ID to base recommendations on
        limit: Maximum number of recommendations to return
    """
    recommendations = await recommend_courses(
        user_id=current_user.id,
        program_id=program_id,
        requirement_based=True,
        limit=limit,
        db=db
    )
    
    return recommendations
