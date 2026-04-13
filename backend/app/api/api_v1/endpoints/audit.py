from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth import get_current_user
from app.db.session import get_async_db
from app.models import User, Program, UserProgram
from app.services.degree_audit import run_degree_audit

router = APIRouter()


@router.get("/", response_model=dict)
async def get_degree_audit(
    plan_id: Optional[int] = None,
    program_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run a degree audit for the current user.
    
    Args:
        plan_id: Optional study plan ID to use for the audit
        program_id: Optional program ID to audit against
    """
    # If program_id is not provided, use the user's primary program
    if not program_id:
        stmt = select(UserProgram).where(
            UserProgram.user_id == current_user.id,
            UserProgram.is_primary == True
        )
        result = await db.execute(stmt)
        user_program = result.scalar_one_or_none()
        
        if not user_program:
            # If no primary program, get any program
            stmt = select(UserProgram).where(UserProgram.user_id == current_user.id)
            result = await db.execute(stmt)
            user_program = result.scalar_one_or_none()
            
            if not user_program:
                raise HTTPException(
                    status_code=404,
                    detail="No program found for this user"
                )
        
        program_id = user_program.program_id
    
    # Verify program exists
    stmt = select(Program).where(Program.id == program_id)
    result = await db.execute(stmt)
    program = result.scalar_one_or_none()
    
    if not program:
        raise HTTPException(
            status_code=404,
            detail="Program not found"
        )
    
    # Run the audit
    audit_results = await run_degree_audit(
        user_id=current_user.id,
        program_id=program_id,
        plan_id=plan_id,
        db=db
    )
    
    return audit_results


@router.get("/programs", response_model=List[dict])
async def get_user_programs(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all programs associated with the current user.
    """
    stmt = select(UserProgram).where(UserProgram.user_id == current_user.id)
    result = await db.execute(stmt)
    user_programs = result.scalars().all()
    
    programs_info = []
    for user_program in user_programs:
        stmt = select(Program).where(Program.id == user_program.program_id)
        result = await db.execute(stmt)
        program = result.scalar_one_or_none()
        
        if program:
            programs_info.append({
                "id": program.id,
                "name": program.name,
                "type": program.type,
                "department": program.department,
                "is_primary": user_program.is_primary
            })
    
    return programs_info
