from fastapi import APIRouter

from app.api.api_v1.endpoints import auth, courses, subjects, users, plans, recommendations, audit

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
