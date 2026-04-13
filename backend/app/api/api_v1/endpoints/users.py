from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth import get_current_user
from app.db.session import get_async_db
from app.models import User, StudyPlan
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create a new user.
    """
    # Check if user with this email already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        year=user_data.year,
        hashed_password=User.get_password_hash(user_data.password),
        is_active=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update current user.
    """
    for field, value in user_update.dict(exclude_unset=True).items():
        if field == "password" and value:
            # Hash the password if it's being updated
            setattr(current_user, "hashed_password", User.get_password_hash(value))
        else:
            setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("/me/plans", response_model=List[dict])
async def get_user_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get all study plans for the current user.
    """
    stmt = select(StudyPlan).where(StudyPlan.user_id == current_user.id)
    result = await db.execute(stmt)
    plans = result.scalars().all()
    
    return [
        {
            "id": plan.id,
            "name": plan.name,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at
        }
        for plan in plans
    ]
