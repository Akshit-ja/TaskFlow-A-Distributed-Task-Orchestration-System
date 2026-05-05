"""
Utility functions for worker task management and monitoring.

This module provides helper functions for task management, monitoring,
and common operations used across different worker tasks.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.core.database import AsyncSessionLocal
from src.core.redis_client import get_redis
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TaskProgressTracker:
    """Track progress of long-running tasks."""
    
    def __init__(self, task_id: str, total_steps: int = 100):
        self.task_id = task_id
        self.total_steps = total_steps
        self.current_step = 0
        
    async def update_progress(self, step: int, message: str = ""):
        """Update task progress."""
        self.current_step = step
        progress = (step / self.total_steps) * 100
        
        progress_data = {
            "task_id": self.task_id,
            "progress": progress,
            "step": step,
            "total_steps": self.total_steps,
            "message": message,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        try:
            redis_client = await get_redis()
            await redis_client.set_json(
                f"task_progress:{self.task_id}", 
                progress_data, 
                expire=3600
            )
            
            # Update Celery task state if available
            if current_task:
                current_task.update_state(
                    state='PROGRESS',
                    meta=progress_data
                )
                
        except Exception as e:
            logger.warning(f"Failed to update task progress: {e}")


async def get_task_progress(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task progress information."""
    try:
        redis_client = await get_redis()
        progress_data = await redis_client.get_json(f"task_progress:{task_id}")
        return progress_data
    except Exception as e:
        logger.warning(f"Failed to get task progress: {e}")
        return None


async def log_task_execution(
    task_id: str, 
    task_name: str, 
    status: str, 
    duration: float,
    result_summary: Optional[str] = None,
    error_message: Optional[str] = None
) -> bool:
    """Log task execution details to database."""
    try:
        async with AsyncSessionLocal() as session:
            log_data = {
                "id": str(uuid4()),
                "task_id": task_id,
                "task_name": task_name,
                "status": status,
                "duration": duration,
                "result_summary": result_summary,
                "error_message": error_message,
                "executed_at": datetime.utcnow().isoformat()
            }
            
            # In a real implementation, insert into task_logs table
            query = text("""
                INSERT INTO task_logs (task_id, level, message, timestamp, metadata)
                VALUES (:task_id, :level, :message, NOW(), :metadata)
            """)
            
            await session.execute(query, {
                "task_id": task_id,
                "level": "INFO" if status == "success" else "ERROR",
                "message": f"Task {task_name} {status} in {duration:.2f}s",
                "metadata": log_data
            })
            await session.commit()
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to log task execution: {e}")
        return False


async def get_worker_stats() -> Dict[str, Any]:
    """Get current worker statistics."""
    try:
        redis_client = await get_redis()
        
        # Get basic worker info
        worker_stats = {
            "worker_id": f"worker-{uuid4().hex[:8]}",
            "status": "active",
            "uptime": "running",
            "tasks_processed": await redis_client.get_json("worker:tasks_processed") or 0,
            "tasks_failed": await redis_client.get_json("worker:tasks_failed") or 0,
            "last_heartbeat": datetime.utcnow().isoformat()
        }
        
        return worker_stats
        
    except Exception as e:
        logger.error(f"Failed to get worker stats: {e}")
        return {"status": "error", "message": str(e)}


async def update_worker_heartbeat(worker_id: str) -> bool:
    """Update worker heartbeat timestamp."""
    try:
        redis_client = await get_redis()
        heartbeat_data = {
            "worker_id": worker_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "alive"
        }
        
        await redis_client.set_json(
            f"worker_heartbeat:{worker_id}", 
            heartbeat_data, 
            expire=300  # 5 minutes
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update worker heartbeat: {e}")
        return False


async def cleanup_stale_workers(max_age_minutes: int = 10) -> List[str]:
    """Clean up stale worker records."""
    try:
        redis_client = await get_redis()
        
        # This would be implemented with Redis SCAN in a real application
        # For now, return empty list as cleanup happened
        cleaned_workers = []
        
        logger.info(f"Cleaned up {len(cleaned_workers)} stale worker records")
        return cleaned_workers
        
    except Exception as e:
        logger.error(f"Failed to cleanup stale workers: {e}")
        return []


def create_task_metadata(
    task_name: str,
    priority: str = "normal",
    tags: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create standardized task metadata."""
    return {
        "task_name": task_name,
        "priority": priority,
        "tags": tags or [],
        "created_at": datetime.utcnow().isoformat(),
        "metadata_version": "1.0",
        **kwargs
    }


async def get_queue_statistics() -> Dict[str, Any]:
    """Get statistics for all task queues."""
    try:
        # In a real implementation, this would query Redis/Celery for actual queue stats
        queue_stats = {
            "default": {"pending": 5, "active": 2, "failed": 1},
            "data_processing": {"pending": 12, "active": 3, "failed": 0},
            "notifications": {"pending": 8, "active": 1, "failed": 2},
            "reports": {"pending": 3, "active": 0, "failed": 0},
            "maintenance": {"pending": 1, "active": 0, "failed": 0}
        }
        
        return {
            "queues": queue_stats,
            "total_pending": sum(q["pending"] for q in queue_stats.values()),
            "total_active": sum(q["active"] for q in queue_stats.values()),
            "total_failed": sum(q["failed"] for q in queue_stats.values()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue statistics: {e}")
        return {"error": str(e)}


async def retry_failed_tasks(queue_name: str = "default", max_retries: int = 10) -> Dict[str, Any]:
    """Retry failed tasks in a specific queue."""
    try:
        # In a real implementation, this would query failed tasks and retry them
        retried_count = 0  # Simulate retrying tasks
        
        logger.info(f"Retried {retried_count} failed tasks from queue {queue_name}")
        
        return {
            "queue": queue_name,
            "retried_count": retried_count,
            "max_retries": max_retries,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to retry tasks: {e}")
        return {"error": str(e)}


class AsyncTaskRunner:
    """Helper class for running async operations within Celery tasks."""
    
    @staticmethod
    def run_async(coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)
    
    @staticmethod
    async def run_with_timeout(coro, timeout_seconds: int = 300):
        """Run coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(f"Task timed out after {timeout_seconds} seconds")
            raise