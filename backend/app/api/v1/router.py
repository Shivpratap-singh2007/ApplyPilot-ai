"""Version 1 API router aggregation."""

from fastapi import APIRouter

from app.api.v1.applications import router as applications_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.privacy import privacy_router, settings_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.resumes import router as resumes_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(profiles_router)
api_v1_router.include_router(resumes_router)
api_v1_router.include_router(applications_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(privacy_router)
