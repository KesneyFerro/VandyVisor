from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Course, CourseUnlock, CourseReachability, BlockCourseMatch, RequirementBlock
from app.models import Completion, Waiver, Plan, PlanTerm, PlanItem, Program, UserProgram
from app.services.course_eligibility import is_course_eligible, get_course_unlocks


async def get_user_remaining_courses(
    db: AsyncSession,
    user_id: int,
    program_id: Optional[int] = None
) -> List[Course]:
    """
    Get the remaining courses a user needs to complete their program(s).
    
    Args:
        db: Database session
        user_id: User ID
        program_id: Optional program ID to filter for a specific program
        
    Returns:
        List[Course]: List of remaining required courses
    """
    # Get user's programs if program_id is not specified
    if program_id is None:
        user_programs = await db.query(UserProgram).filter(
            UserProgram.user_id == user_id
        ).all()
        program_ids = [up.program_id for up in user_programs]
    else:
        program_ids = [program_id]
    
    # Get all requirement blocks for the programs
    blocks = await db.query(RequirementBlock).filter(
        RequirementBlock.program_id.in_(program_ids)
    ).all()
    
    # Get all course matches for these blocks
    course_matches = await db.query(BlockCourseMatch).filter(
        BlockCourseMatch.block_id.in_([block.id for block in blocks])
    ).all()
    
    # Get all courses that match these blocks
    required_course_ids = [cm.course_id for cm in course_matches]
    
    # Get the user's completed courses
    completions = await db.query(Completion).filter(
        Completion.user_id == user_id
    ).all()
    completed_course_ids = [c.course_id for c in completions]
    
    # Get the user's waived courses
    waivers = await db.query(Waiver).filter(
        Waiver.user_id == user_id,
        Waiver.waiver_type == 'course'
    ).all()
    waived_course_ids = [w.required_course_id for w in waivers]
    
    # Filter out completed and waived courses
    remaining_course_ids = [
        course_id for course_id in required_course_ids 
        if course_id not in completed_course_ids and course_id not in waived_course_ids
    ]
    
    # Get the actual course objects
    remaining_courses = await db.query(Course).filter(
        Course.id.in_(remaining_course_ids)
    ).all()
    
    return remaining_courses


async def calculate_course_unlock_score(
    db: AsyncSession,
    course_id: int,
    remaining_courses: List[Course]
) -> Dict[str, Any]:
    """
    Calculate the unlock score for a course based on how many remaining courses it unlocks.
    
    Args:
        db: Database session
        course_id: Course ID
        remaining_courses: List of remaining required courses
        
    Returns:
        Dict: Dictionary with direct and transitive unlock scores
    """
    # Get the direct unlocks
    direct_unlocks = await get_course_unlocks(db, course_id)
    direct_unlock_ids = [c.id for c in direct_unlocks]
    
    # Calculate how many remaining courses are directly unlocked
    direct_remaining_unlocks = len([
        c for c in remaining_courses if c.id in direct_unlock_ids
    ])
    
    # Get the transitive unlocks
    query = """
    SELECT 
        cr.reachable_course_id, 
        cr.distance
    FROM course_reachability cr
    WHERE cr.source_course_id = :course_id
    """
    
    result = await db.execute(text(query), {"course_id": course_id})
    reachability_data = result.mappings().all()
    
    # Calculate the transitive score
    transitive_score = 0.0
    for row in reachability_data:
        if row['reachable_course_id'] in [c.id for c in remaining_courses]:
            # Weight by inverse of distance (closer = higher score)
            transitive_score += 1.0 / row['distance']
    
    return {
        "course_id": course_id,
        "direct_score": direct_remaining_unlocks,
        "transitive_score": transitive_score,
        "total_score": direct_remaining_unlocks + transitive_score
    }


async def recommend_courses(
    db: AsyncSession,
    user_id: int,
    term_code: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Recommend courses for a user based on their eligibility and unlock scores.
    
    Args:
        db: Database session
        user_id: User ID
        term_code: Optional term code for term-specific recommendations
        limit: Maximum number of recommendations to return
        
    Returns:
        List[Dict]: Recommended courses with scores
    """
    # Get the remaining courses
    remaining_courses = await get_user_remaining_courses(db, user_id)
    
    # Get all courses and filter by eligibility
    courses = await db.query(Course).all()
    eligible_courses = []
    for course in courses:
        if await is_course_eligible(db, user_id, course.id, term_code):
            eligible_courses.append(course)
    
    # Calculate unlock scores for each eligible course
    recommendations = []
    for course in eligible_courses:
        score = await calculate_course_unlock_score(db, course.id, remaining_courses)
        
        # Add the course details to the recommendation
        recommendation = {
            "course_id": course.id,
            "subject_code": course.subject_code,
            "catalog_number": course.catalog_number,
            "title": course.title,
            "credits": float(course.units_earned),
            "direct_score": score["direct_score"],
            "transitive_score": score["transitive_score"],
            "total_score": score["total_score"]
        }
        
        recommendations.append(recommendation)
    
    # Sort by total score (descending) and limit results
    recommendations.sort(key=lambda x: x["total_score"], reverse=True)
    return recommendations[:limit]


async def recommend_path_to_graduation(
    db: AsyncSession,
    user_id: int,
    max_terms: int = 8
) -> List[Dict[str, Any]]:
    """
    Recommend a path to graduation by planning multiple terms ahead.
    
    Args:
        db: Database session
        user_id: User ID
        max_terms: Maximum number of terms to plan
        
    Returns:
        List[Dict]: Recommended path with terms and courses
    """
    # Get the user's program(s)
    user_programs = await db.query(UserProgram).filter(
        UserProgram.user_id == user_id
    ).all()
    
    # Get the remaining courses
    remaining_courses = await get_user_remaining_courses(db, user_id)
    
    # Get the eligible courses for the first term
    courses = await db.query(Course).all()
    eligible_courses = []
    for course in courses:
        if await is_course_eligible(db, user_id, course.id):
            eligible_courses.append(course)
    
    # Plan multiple terms
    path = []
    for term_index in range(max_terms):
        # Skip if no remaining courses
        if not remaining_courses:
            break
            
        # Calculate scores for eligible courses
        term_recommendations = []
        for course in eligible_courses:
            score = await calculate_course_unlock_score(db, course.id, remaining_courses)
            term_recommendations.append({
                "course": course,
                "score": score["total_score"]
            })
        
        # Sort by score (highest first)
        term_recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        # Take the top courses (max 5 per term, or 12-18 credits)
        selected_courses = []
        term_credits = 0
        for rec in term_recommendations:
            if len(selected_courses) >= 5:
                break
                
            course = rec["course"]
            course_credits = float(course.units_earned)
            
            # Check if adding this course would exceed 18 credits
            if term_credits + course_credits > 18:
                continue
                
            selected_courses.append(course)
            term_credits += course_credits
            
            # If we've reached the minimum of 12 credits, we can stop
            # (but continue to try to fill up to 18 credits if possible)
            if term_credits >= 12 and len(selected_courses) >= 3:
                break
        
        # Add the term to the path
        path.append({
            "term_index": term_index,
            "courses": selected_courses,
            "credits": term_credits
        })
        
        # Update the remaining courses list by removing selected courses
        remaining_courses = [c for c in remaining_courses if c.id not in [sc.id for sc in selected_courses]]
        
        # Update eligible courses for the next term
        # (simulate completion of selected courses)
        for course in selected_courses:
            # Add new courses that would become eligible
            unlocks = await get_course_unlocks(db, course.id)
            for unlocked in unlocks:
                if await is_course_eligible(db, user_id, unlocked.id):
                    if unlocked not in eligible_courses:
                        eligible_courses.append(unlocked)
        
        # Remove selected courses from eligible list
        eligible_courses = [c for c in eligible_courses if c.id not in [sc.id for sc in selected_courses]]
    
    return path
