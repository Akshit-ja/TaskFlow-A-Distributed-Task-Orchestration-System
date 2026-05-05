"""
Monitoring router for the distributed task queue API.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.core.database import get_async_db

router = APIRouter()


# Pydantic models for response
class SystemStats(BaseModel):
    """System statistics model."""
    total_tasks: int
    pending_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    queues: Dict[str, int]
    workers: Dict[str, str]


class TaskMetrics(BaseModel):
    """Task metrics model."""
    task_name: str
    total_count: int
    success_count: int
    failure_count: int
    avg_duration: float
    last_executed: Optional[datetime]


class QueueStats(BaseModel):
    """Queue statistics model."""
    queue_name: str
    pending_tasks: int
    active_tasks: int
    scheduled_tasks: int
    failed_tasks: int


class WorkerInfo(BaseModel):
    """Worker information model."""
    worker_id: str
    status: str
    current_task: Optional[str]
    processed_tasks: int
    failed_tasks: int
    last_heartbeat: datetime


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    db: AsyncSession = Depends(get_async_db)
):
    """Get overall system statistics."""
    # Mock data for now
    return SystemStats(
        total_tasks=1000,
        pending_tasks=50,
        running_tasks=10,
        completed_tasks=900,
        failed_tasks=40,
        queues={
            "default": 25,
            "high_priority": 15,
            "background": 10
        },
        workers={
            "worker-1": "active",
            "worker-2": "active",
            "worker-3": "idle"
        }
    )


@router.get("/metrics", response_model=List[TaskMetrics])
async def get_task_metrics(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_async_db)
):
    """Get task execution metrics for the specified time period."""
    # Mock data for now
    return [
        TaskMetrics(
            task_name="data_processing",
            total_count=500,
            success_count=480,
            failure_count=20,
            avg_duration=120.5,
            last_executed=datetime.utcnow() - timedelta(minutes=5)
        ),
        TaskMetrics(
            task_name="email_notification",
            total_count=200,
            success_count=195,
            failure_count=5,
            avg_duration=2.3,
            last_executed=datetime.utcnow() - timedelta(minutes=1)
        ),
        TaskMetrics(
            task_name="report_generation",
            total_count=50,
            success_count=45,
            failure_count=5,
            avg_duration=300.7,
            last_executed=datetime.utcnow() - timedelta(hours=2)
        )
    ]


@router.get("/queues", response_model=List[QueueStats])
async def get_queue_stats(
    db: AsyncSession = Depends(get_async_db)
):
    """Get statistics for all queues."""
    # Mock data for now
    return [
        QueueStats(
            queue_name="default",
            pending_tasks=25,
            active_tasks=5,
            scheduled_tasks=3,
            failed_tasks=2
        ),
        QueueStats(
            queue_name="high_priority",
            pending_tasks=15,
            active_tasks=3,
            scheduled_tasks=1,
            failed_tasks=1
        ),
        QueueStats(
            queue_name="background",
            pending_tasks=10,
            active_tasks=2,
            scheduled_tasks=0,
            failed_tasks=0
        )
    ]


@router.get("/workers", response_model=List[WorkerInfo])
async def get_worker_info(
    db: AsyncSession = Depends(get_async_db)
):
    """Get information about all workers."""
    # Mock data for now
    return [
        WorkerInfo(
            worker_id="worker-1",
            status="active",
            current_task="data_processing_task_123",
            processed_tasks=150,
            failed_tasks=5,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=10)
        ),
        WorkerInfo(
            worker_id="worker-2",
            status="active",
            current_task="email_notification_task_456",
            processed_tasks=200,
            failed_tasks=3,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=15)
        ),
        WorkerInfo(
            worker_id="worker-3",
            status="idle",
            current_task=None,
            processed_tasks=100,
            failed_tasks=2,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=5)
        )
    ]


@router.get("/errors")
async def get_error_summary(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_async_db)
):
    """Get error summary for the specified time period."""
    # Mock data for now
    return {
        "time_period": f"{hours} hours",
        "total_errors": 45,
        "error_types": {
            "ConnectionError": 20,
            "TimeoutError": 15,
            "ValueError": 7,
            "KeyError": 3
        },
        "error_trends": [
            {"hour": i, "count": max(0, 10 - abs(i - 12))}
            for i in range(24)
        ]
    }


@router.get("/performance")
async def get_performance_metrics(
    db: AsyncSession = Depends(get_async_db)
):
    """Get performance metrics."""
    # Mock data for now
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "throughput": {
            "tasks_per_minute": 8.5,
            "tasks_per_hour": 510,
            "peak_throughput": 15.2
        },
        "latency": {
            "avg_queue_time": 2.3,
            "avg_execution_time": 45.7,
            "avg_total_time": 48.0
        },
        "resource_usage": {
            "cpu_usage_percent": 65.2,
            "memory_usage_mb": 512,
            "redis_memory_mb": 128,
            "database_connections": 5
        }
    }


@router.post("/alerts/test")
async def test_alert(
    alert_type: str = Query(...),
    db: AsyncSession = Depends(get_async_db)
):
    """Test alert system with different alert types."""
    return {
        "message": f"Test alert of type '{alert_type}' sent successfully",
        "timestamp": datetime.utcnow().isoformat(),
        "alert_id": f"test-alert-{datetime.utcnow().timestamp()}"
    }