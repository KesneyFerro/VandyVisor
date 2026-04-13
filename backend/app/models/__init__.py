from app.models.user import User
from app.models.catalog import Subject, Term, Course
from app.models.course_details import CourseOffering, Attribute, CourseAttribute, RequisiteGroup, RequisiteGroupMember, CourseEquivalent
from app.models.programs import Program, RequirementBlock, BlockCourseMatch, CourseUnlock, CourseReachability
from app.models.user_data import UserProgram, Preference, Completion, Waiver
from app.models.plans import Plan, PlanTerm, PlanItem, AuditRun, Recommendation, UserAuditRow

# For Alembic migrations
from app.db.base import Base
