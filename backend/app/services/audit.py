from typing import List, Dict, Any, Optional, Tuple
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Program, RequirementBlock, BlockCourseMatch, Course
from app.models import Completion, Waiver, Plan, PlanTerm, PlanItem


async def evaluate_requirement_block(
    db: AsyncSession,
    user_id: int,
    block_id: int,
    include_planned: bool = False,
    plan_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Evaluate a requirement block for a specific user.
    
    Args:
        db: Database session
        user_id: User ID
        block_id: Requirement block ID
        include_planned: Whether to include planned courses
        plan_id: Optional plan ID to use for planned courses
        
    Returns:
        Dict: Block evaluation results
    """
    # Get the block
    block = await db.query(RequirementBlock).filter(
        RequirementBlock.id == block_id
    ).first()
    
    if not block:
        return {
            "block_id": block_id,
            "status": "error",
            "message": "Block not found"
        }
    
    # Check if there's a waiver for this block
    waiver = await db.query(Waiver).filter(
        Waiver.user_id == user_id,
        Waiver.block_id == block_id,
        Waiver.waiver_type == 'block'
    ).first()
    
    if waiver:
        return {
            "block_id": block_id,
            "name": block.name,
            "status": "satisfied",
            "credits_required": float(block.required_credits) if block.required_credits else 0,
            "credits_completed": float(block.required_credits) if block.required_credits else 0,
            "credits_remaining": 0,
            "is_waived": True,
            "waiver_reason": waiver.reason,
            "courses_completed": [],
            "courses_planned": []
        }
    
    # Get the rule for this block
    rule = block.rule
    
    # Get courses that can satisfy this block
    block_courses = await db.query(BlockCourseMatch).filter(
        BlockCourseMatch.block_id == block_id
    ).all()
    
    course_ids = [bc.course_id for bc in block_courses]
    
    # Get completions for this user
    completions = await db.query(Completion).filter(
        Completion.user_id == user_id,
        Completion.course_id.in_(course_ids)
    ).all()
    
    completed_course_ids = [c.course_id for c in completions]
    completed_courses = await db.query(Course).filter(
        Course.id.in_(completed_course_ids)
    ).all()
    
    # Get planned courses if requested
    planned_courses = []
    if include_planned and plan_id:
        plan_terms = await db.query(PlanTerm).filter(
            PlanTerm.plan_id == plan_id
        ).all()
        
        plan_term_ids = [pt.id for pt in plan_terms]
        
        plan_items = await db.query(PlanItem).filter(
            PlanItem.plan_term_id.in_(plan_term_ids),
            PlanItem.course_id.in_(course_ids)
        ).all()
        
        planned_course_ids = [pi.course_id for pi in plan_items]
        planned_courses = await db.query(Course).filter(
            Course.id.in_(planned_course_ids)
        ).all()
    
    # Calculate credits completed and remaining
    completed_credits = sum([float(c.units_earned) for c in completed_courses])
    planned_credits = sum([float(c.units_earned) for c in planned_courses])
    
    # Determine if the block is satisfied
    satisfied = False
    credits_required = float(block.required_credits) if block.required_credits else 0
    credits_remaining = max(0, credits_required - completed_credits)
    
    if rule["type"] == "all":
        # All specified courses must be completed
        if "of" in rule:
            required_courses = []
            for course_spec in rule["of"]:
                if "course" in course_spec:
                    subject, catalog = course_spec["course"].split()
                    course = await db.query(Course).filter(
                        Course.subject_code == subject,
                        Course.catalog_number == catalog
                    ).first()
                    if course:
                        required_courses.append(course)
            
            # Check if all required courses are completed
            required_ids = [c.id for c in required_courses]
            satisfied = all(course_id in completed_course_ids for course_id in required_ids)
    
    elif rule["type"] == "min_credits":
        # Minimum credits from courses matching filters
        min_credits = rule.get("credits", 0)
        satisfied = completed_credits >= min_credits
    
    # Include planned courses in satisfaction check if requested
    if include_planned and not satisfied:
        if rule["type"] == "all" and "of" in rule:
            required_ids = [c.id for c in required_courses]
            planned_ids = [c.id for c in planned_courses]
            combined_ids = completed_course_ids + planned_ids
            satisfied = all(course_id in combined_ids for course_id in required_ids)
        
        elif rule["type"] == "min_credits":
            min_credits = rule.get("credits", 0)
            satisfied = (completed_credits + planned_credits) >= min_credits
    
    status = "satisfied" if satisfied else "in_progress" if completed_credits > 0 else "not_started"
    
    return {
        "block_id": block_id,
        "name": block.name,
        "description": block.description,
        "status": status,
        "credits_required": credits_required,
        "credits_completed": completed_credits,
        "credits_planned": planned_credits if include_planned else 0,
        "credits_remaining": credits_remaining,
        "is_waived": False,
        "courses_completed": [
            {
                "id": c.id,
                "subject_code": c.subject_code,
                "catalog_number": c.catalog_number,
                "title": c.title,
                "credits": float(c.units_earned)
            }
            for c in completed_courses
        ],
        "courses_planned": [
            {
                "id": c.id,
                "subject_code": c.subject_code,
                "catalog_number": c.catalog_number,
                "title": c.title,
                "credits": float(c.units_earned)
            }
            for c in planned_courses
        ] if include_planned else []
    }


async def run_degree_audit(
    db: AsyncSession,
    user_id: int,
    program_id: int,
    include_planned: bool = False,
    plan_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run a full degree audit for a user and program.
    
    Args:
        db: Database session
        user_id: User ID
        program_id: Program ID
        include_planned: Whether to include planned courses
        plan_id: Optional plan ID to use for planned courses
        
    Returns:
        Dict: Complete audit results
    """
    # Get the program
    program = await db.query(Program).filter(
        Program.id == program_id
    ).first()
    
    if not program:
        return {
            "status": "error",
            "message": "Program not found"
        }
    
    # Get the top-level requirement blocks for this program
    blocks = await db.query(RequirementBlock).filter(
        RequirementBlock.program_id == program_id,
        RequirementBlock.parent_block_id.is_(None)
    ).all()
    
    # Evaluate each block
    block_results = []
    total_credits_required = 0
    total_credits_completed = 0
    total_credits_planned = 0
    
    for block in blocks:
        result = await evaluate_requirement_block(
            db, user_id, block.id, include_planned, plan_id
        )
        block_results.append(result)
        
        total_credits_required += result["credits_required"]
        total_credits_completed += result["credits_completed"]
        total_credits_planned += result.get("credits_planned", 0)
    
    # Calculate overall completion percentage
    completion_percentage = 0
    if total_credits_required > 0:
        completion_percentage = (total_credits_completed / total_credits_required) * 100
        completion_percentage = min(100, round(completion_percentage, 1))
    
    # Determine overall status
    overall_status = "not_started"
    if all(result["status"] == "satisfied" for result in block_results):
        overall_status = "satisfied"
    elif any(result["status"] in ["satisfied", "in_progress"] for result in block_results):
        overall_status = "in_progress"
    
    return {
        "program_id": program_id,
        "program_name": program.name,
        "program_type": program.type,
        "catalog_year": program.catalog_year,
        "status": overall_status,
        "completion_percentage": completion_percentage,
        "credits_required": total_credits_required,
        "credits_completed": total_credits_completed,
        "credits_planned": total_credits_planned,
        "credits_remaining": max(0, total_credits_required - total_credits_completed),
        "blocks": block_results,
        "run_date": None  # Will be set by the API endpoint
    }
