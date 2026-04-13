from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Course, RequisiteGroup, RequisiteGroupMember, Completion


async def is_course_eligible(
    db: AsyncSession, 
    user_id: int, 
    course_id: int, 
    term_code: Optional[str] = None
) -> bool:
    """
    Check if a user is eligible to take a specific course.
    
    Args:
        db: Database session
        user_id: User ID
        course_id: Course ID
        term_code: Optional term code for checking term-specific eligibility
        
    Returns:
        bool: True if eligible, False otherwise
    """
    # Check if the course exists
    course = await db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return False
        
    # Check if the user has already completed this course
    completed = await db.query(Completion).filter(
        Completion.user_id == user_id,
        Completion.course_id == course_id
    ).first()
    if completed:
        return False
    
    # Get all prereq groups for this course
    prereq_groups = await db.query(RequisiteGroup).filter(
        RequisiteGroup.course_id == course_id,
        RequisiteGroup.kind == 'pre'
    ).all()
    
    # If there are no prerequisites, the course is eligible
    if not prereq_groups:
        return True
        
    # For each prereq group, check if it's satisfied
    for group in prereq_groups:
        # Get all members of this group
        members = await db.query(RequisiteGroupMember).filter(
            RequisiteGroupMember.group_id == group.id
        ).all()
        
        if group.logic == 'all':
            # All members must be satisfied
            all_satisfied = True
            for member in members:
                # Check if the user has completed this course
                if member.target_course_id:
                    completed = await db.query(Completion).filter(
                        Completion.user_id == user_id,
                        Completion.course_id == member.target_course_id
                    ).first()
                    if not completed:
                        all_satisfied = False
                        break
                else:
                    # Handle subject-level prerequisite
                    completed = await db.query(Completion).join(Course).filter(
                        Completion.user_id == user_id,
                        Course.subject_code == member.target_subject,
                        Course.catalog_number == member.target_catalog
                    ).first()
                    if not completed:
                        all_satisfied = False
                        break
                        
            if all_satisfied:
                # This group is satisfied, check the next one
                continue
            else:
                # This group is not satisfied, check if there's another satisfied group
                continue
        
        elif group.logic == 'min_count':
            # At least min_count members must be satisfied
            satisfied_count = 0
            for member in members:
                # Check if the user has completed this course
                if member.target_course_id:
                    completed = await db.query(Completion).filter(
                        Completion.user_id == user_id,
                        Completion.course_id == member.target_course_id
                    ).first()
                    if completed:
                        satisfied_count += 1
                else:
                    # Handle subject-level prerequisite
                    completed = await db.query(Completion).join(Course).filter(
                        Completion.user_id == user_id,
                        Course.subject_code == member.target_subject,
                        Course.catalog_number == member.target_catalog
                    ).first()
                    if completed:
                        satisfied_count += 1
                        
            if satisfied_count >= group.min_count:
                # This group is satisfied, check the next one
                continue
            else:
                # This group is not satisfied, check if there's another satisfied group
                continue
    
    # Check for anti-requisites
    anti_groups = await db.query(RequisiteGroup).filter(
        RequisiteGroup.course_id == course_id,
        RequisiteGroup.kind == 'anti'
    ).all()
    
    for group in anti_groups:
        # Get all members of this group
        members = await db.query(RequisiteGroupMember).filter(
            RequisiteGroupMember.group_id == group.id
        ).all()
        
        if group.logic == 'all':
            # If all members are completed, the course is not eligible
            all_completed = True
            for member in members:
                # Check if the user has completed this course
                if member.target_course_id:
                    completed = await db.query(Completion).filter(
                        Completion.user_id == user_id,
                        Completion.course_id == member.target_course_id
                    ).first()
                    if not completed:
                        all_completed = False
                        break
                else:
                    # Handle subject-level anti-requisite
                    completed = await db.query(Completion).join(Course).filter(
                        Completion.user_id == user_id,
                        Course.subject_code == member.target_subject,
                        Course.catalog_number == member.target_catalog
                    ).first()
                    if not completed:
                        all_completed = False
                        break
                        
            if all_completed:
                # All anti-requisites are completed, the course is not eligible
                return False
        
        elif group.logic == 'min_count':
            # If at least min_count members are completed, the course is not eligible
            completed_count = 0
            for member in members:
                # Check if the user has completed this course
                if member.target_course_id:
                    completed = await db.query(Completion).filter(
                        Completion.user_id == user_id,
                        Completion.course_id == member.target_course_id
                    ).first()
                    if completed:
                        completed_count += 1
                else:
                    # Handle subject-level anti-requisite
                    completed = await db.query(Completion).join(Course).filter(
                        Completion.user_id == user_id,
                        Course.subject_code == member.target_subject,
                        Course.catalog_number == member.target_catalog
                    ).first()
                    if completed:
                        completed_count += 1
                        
            if completed_count >= group.min_count:
                # Min count anti-requisites are completed, the course is not eligible
                return False
    
    # If we reach here, all prereq groups are satisfied and no anti-requisites are triggered
    return True


async def get_user_eligible_courses(
    db: AsyncSession, 
    user_id: int, 
    term_code: Optional[str] = None
) -> List[Course]:
    """
    Get all courses that a user is eligible to take.
    
    Args:
        db: Database session
        user_id: User ID
        term_code: Optional term code for checking term-specific eligibility
        
    Returns:
        List[Course]: List of eligible courses
    """
    # Get all courses
    courses = await db.query(Course).all()
    
    # Filter courses by eligibility
    eligible_courses = []
    for course in courses:
        if await is_course_eligible(db, user_id, course.id, term_code):
            eligible_courses.append(course)
            
    return eligible_courses


async def get_course_unlocks(db: AsyncSession, course_id: int) -> List[Course]:
    """
    Get the courses that are unlocked by completing a specific course.
    
    Args:
        db: Database session
        course_id: Course ID
        
    Returns:
        List[Course]: List of courses unlocked by this course
    """
    # Use the precomputed course_unlocks table
    query = """
    SELECT c.*
    FROM courses c
    JOIN course_unlocks cu ON c.id = cu.unlocks_course_id
    WHERE cu.course_id = :course_id
    """
    
    result = await db.execute(text(query), {"course_id": course_id})
    return result.mappings().all()


async def get_course_reachability(db: AsyncSession, course_id: int) -> List[Dict[str, Any]]:
    """
    Get the transitive reachability of courses from a given course.
    
    Args:
        db: Database session
        course_id: Course ID
        
    Returns:
        List[Dict]: List of reachable courses with distance
    """
    # Use the precomputed course_reachability table
    query = """
    SELECT 
        c.id, 
        c.subject_code, 
        c.catalog_number, 
        c.title, 
        cr.distance
    FROM course_reachability cr
    JOIN courses c ON c.id = cr.reachable_course_id
    WHERE cr.source_course_id = :course_id
    ORDER BY cr.distance ASC
    """
    
    result = await db.execute(text(query), {"course_id": course_id})
    return result.mappings().all()
