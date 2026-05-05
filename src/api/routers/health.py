"""
Health check router for the distributed task queue API.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.core.database import get_async_db
from src.core.redis_client import get_redis

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "distributed-task-queue-api"
    }


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_async_db)):
    """Detailed health check including database and Redis connectivity."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "distributed-task-queue-api",
        "checks": {
            "database": "unknown",
            "redis": "unknown"
        }
    }
    
    # Check database connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis connectivity
    try:
        redis_client = await get_redis()
        await redis_client.health_check()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}