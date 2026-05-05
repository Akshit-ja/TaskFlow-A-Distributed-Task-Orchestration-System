"""
FastAPI application setup and router inclusion.
"""

from fastapi import FastAPI, APIRouter

from src.api.routers.health import router as health_router
from src.api.routers.tasks import router as tasks_router
from src.api.routers.monitoring import router as monitoring_router

app = FastAPI(title="Distributed Task Queue - API v1")

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])

# Mount into app
app.include_router(api_router)
