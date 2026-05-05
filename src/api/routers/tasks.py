"""
Task management router for the distributed task queue API.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from celery import Celery
from src.core.config import get_settings

# Initialize Celery app for task submission
settings = get_settings()
celery_app = Celery(
    'distributed_task_queue',
    broker=f'redis://redis:6379/0',
    backend=f'redis://redis:6379/0'
)

router = APIRouter()


def _priority_to_db(priority: int) -> str:
    if priority <= 2:
        return "low"
    if priority <= 5:
        return "normal"
    if priority <= 8:
        return "high"
    return "critical"


def _priority_to_response(priority: Optional[str]) -> int:
    mapping = {
        "low": 2,
        "normal": 5,
        "high": 8,
        "critical": 10,
    }
    return mapping.get((priority or "normal").lower(), 5)


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _task_row_to_response(row: Any) -> "TaskResponse":
    data = row._mapping if hasattr(row, "_mapping") else row
    metadata = _json_value(data.get("metadata")) or {}
    payload = _json_value(data.get("payload")) or {}
    result = _json_value(data.get("result"))
    status = str(data.get("status") or "pending").upper()
    updated_at = data.get("updated_at") or data.get("completed_at") or data.get("started_at") or data.get("created_at")

    return TaskResponse(
        id=str(data["id"]),
        name=data.get("name") or metadata.get("task_name") or metadata.get("task_type") or "task",
        function_name=data.get("function_name") or metadata.get("function_name") or metadata.get("task_type") or "task",
        status=status,
        priority=_priority_to_response(data.get("priority")),
        retry_count=int(data.get("current_retries") or 0),
        max_retries=int(data.get("max_retries") or 3),
        created_at=data.get("created_at") or datetime.utcnow(),
        updated_at=updated_at or datetime.utcnow(),
        result=result,
        error_message=data.get("error_message"),
    )


async def _fetch_task(db: AsyncSession, task_id: str):
    query = text(
        """
        SELECT
            id,
            name,
            queue_name,
            priority,
            status,
            payload,
            result,
            error_message,
            max_retries,
            current_retries,
            retry_delay,
            timeout,
            created_at,
            scheduled_at,
            started_at,
            completed_at,
            worker_id,
            worker_hostname,
            tags,
            metadata,
            GREATEST(
                created_at,
                COALESCE(started_at, created_at),
                COALESCE(completed_at, created_at),
                COALESCE(scheduled_at, created_at)
            ) AS updated_at
        FROM tasks
        WHERE id = CAST(:task_id AS UUID)
        """
    )
    result = await db.execute(query, {"task_id": task_id})
    return result.mappings().first()


async def _persist_task(
    db: AsyncSession,
    *,
    task_id: str,
    name: str,
    function_name: str,
    queue_name: str,
    payload: Dict[str, Any],
    status: str,
    priority: int = 5,
    max_retries: int = 3,
    retry_count: int = 0,
    timeout: Optional[int] = 300,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    query = text(
        """
        INSERT INTO tasks (
            id, name, queue_name, priority, status, payload, result, error_message,
            max_retries, current_retries, retry_delay, timeout, created_at,
            scheduled_at, started_at, completed_at, worker_id, worker_hostname,
            tags, metadata
        ) VALUES (
            CAST(:task_id AS UUID), :name, :queue_name, CAST(:priority AS task_priority),
            CAST(:status AS task_status), CAST(:payload AS JSONB), CAST(:result AS JSONB),
            :error_message, :max_retries, :retry_count, :retry_delay, :timeout,
            NOW(), NOW(), NULL, NULL, NULL, NULL, CAST(:tags AS JSONB), CAST(:metadata AS JSONB)
        )
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            queue_name = EXCLUDED.queue_name,
            priority = EXCLUDED.priority,
            status = EXCLUDED.status,
            payload = EXCLUDED.payload,
            result = EXCLUDED.result,
            error_message = EXCLUDED.error_message,
            max_retries = EXCLUDED.max_retries,
            current_retries = EXCLUDED.current_retries,
            retry_delay = EXCLUDED.retry_delay,
            timeout = EXCLUDED.timeout,
            metadata = EXCLUDED.metadata
        """
    )
    await db.execute(
        query,
        {
            "task_id": task_id,
            "name": name,
            "queue_name": queue_name,
            "priority": _priority_to_db(priority),
            "status": status.lower(),
            "payload": json.dumps(payload or {}),
            "result": json.dumps(result) if result is not None else None,
            "error_message": error_message,
            "max_retries": max_retries,
            "retry_count": retry_count,
            "retry_delay": 60,
            "timeout": timeout,
            "tags": json.dumps([]),
            "metadata": json.dumps(metadata or {}),
        },
    )
    await db.commit()


# Pydantic models for request/response
class TaskCreate(BaseModel):
    """Task creation request model."""
    name: str
    function_name: str
    args: Optional[dict] = None
    kwargs: Optional[dict] = None
    priority: int = 5
    retry_count: int = 3
    timeout: Optional[int] = 300


class TaskResponse(BaseModel):
    """Task response model."""
    id: str
    name: str
    function_name: str
    status: str
    priority: int
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    result: Optional[dict] = None
    error_message: Optional[str] = None


class TaskUpdate(BaseModel):
    """Task update request model."""
    status: Optional[str] = None
    priority: Optional[int] = None
    retry_count: Optional[int] = None


class TaskSubmissionRequest(BaseModel):
    """Task submission request model."""
    task_type: str  # 'process_data', 'send_notification', 'generate_report', etc.
    data: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None


class TaskSubmissionResponse(BaseModel):
    """Task submission response model."""
    task_id: str
    task_type: str
    status: str
    submitted_at: datetime


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new task in the queue."""
    task_id = celery_app.send_task(
        task.function_name,
        args=task.args or [],
        kwargs=task.kwargs or {},
    ).id

    await _persist_task(
        db,
        task_id=task_id,
        name=task.name,
        function_name=task.function_name,
        queue_name="default",
        payload={"args": task.args or {}, "kwargs": task.kwargs or {}},
        status="pending",
        priority=task.priority,
        max_retries=task.retry_count,
        retry_count=0,
        timeout=task.timeout,
        metadata={"source": "api", "function_name": task.function_name},
    )

    row = await _fetch_task(db, task_id)
    if row is None:
        raise HTTPException(status_code=500, detail="Task was created in Celery but could not be saved to the database")
    return _task_row_to_response(row)


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    """List tasks with optional filtering."""
    where_clause = ""
    params: Dict[str, Any] = {"skip": skip, "limit": limit}
    if status:
        where_clause = "WHERE status = CAST(:status AS task_status)"
        params["status"] = status.lower()

    query = text(
        f"""
        SELECT
            id,
            name,
            queue_name,
            priority,
            status,
            payload,
            result,
            error_message,
            max_retries,
            current_retries,
            retry_delay,
            timeout,
            created_at,
            scheduled_at,
            started_at,
            completed_at,
            worker_id,
            worker_hostname,
            tags,
            metadata,
            GREATEST(
                created_at,
                COALESCE(started_at, created_at),
                COALESCE(completed_at, created_at),
                COALESCE(scheduled_at, created_at)
            ) AS updated_at
        FROM tasks
        {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :skip
        """
    )
    result = await db.execute(query, params)
    rows = result.mappings().all()
    return [_task_row_to_response(row) for row in rows]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific task by ID."""
    row = await _fetch_task(db, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_row_to_response(row)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    """Update a task's status or other properties."""
    row = await _fetch_task(db, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    current = row
    new_status = (task_update.status or current["status"]).lower()
    new_priority = _priority_to_db(task_update.priority or _priority_to_response(current["priority"]))
    new_retry_count = task_update.retry_count if task_update.retry_count is not None else int(current["current_retries"] or 0)

    query = text(
        """
        UPDATE tasks
        SET
            status = CAST(:status AS task_status),
            priority = CAST(:priority AS task_priority),
            current_retries = :current_retries,
            completed_at = CASE WHEN CAST(:status AS task_status) IN ('completed', 'failed', 'cancelled') THEN COALESCE(completed_at, NOW()) ELSE completed_at END,
            started_at = CASE WHEN CAST(:status AS task_status) = 'running' THEN COALESCE(started_at, NOW()) ELSE started_at END
        WHERE id = CAST(:task_id AS UUID)
        """
    )
    await db.execute(query, {"task_id": task_id, "status": new_status, "priority": new_priority, "current_retries": new_retry_count})
    await db.commit()

    updated = await _fetch_task(db, task_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_row_to_response(updated)


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Cancel a pending task."""
    row = await _fetch_task(db, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.execute(
        text("UPDATE tasks SET status = 'cancelled', completed_at = NOW() WHERE id = CAST(:task_id AS UUID)"),
        {"task_id": task_id},
    )
    await db.commit()
    return {"message": f"Task {task_id} has been cancelled"}


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Retry a failed task."""
    row = await _fetch_task(db, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.execute(
        text("UPDATE tasks SET status = 'retrying', current_retries = current_retries + 1, scheduled_at = NOW() WHERE id = CAST(:task_id AS UUID)"),
        {"task_id": task_id},
    )
    await db.commit()
    return {"message": f"Task {task_id} has been queued for retry"}


@router.get("/{task_id}/result")
async def get_task_result(
    task_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Get the result of a completed task."""
    row = await _fetch_task(db, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    data = row
    return {
        "task_id": task_id,
        "status": str(data.get("status") or "pending").upper(),
        "result": _json_value(data.get("result")),
        "completed_at": (data.get("completed_at") or data.get("updated_at") or data.get("created_at")).isoformat() if hasattr(data.get("completed_at") or data.get("updated_at") or data.get("created_at"), "isoformat") else str(data.get("completed_at") or data.get("updated_at") or data.get("created_at"))
    }


@router.post("/submit", response_model=TaskSubmissionResponse, status_code=201)
async def submit_task(
    task_request: TaskSubmissionRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Submit a new task to the Celery worker queue."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Determine which Celery task to call based on task_type
        task_functions = {
            "process_data": "process_data",
            "send_notification": "send_notification", 
            "generate_report": "generate_report",
            "cleanup_data": "cleanup_old_data",
            "health_check": "health_check"
        }
        
        if task_request.task_type not in task_functions:
            raise HTTPException(status_code=400, detail=f"Unknown task type: {task_request.task_type}")
        
        # Prepare task arguments based on task type
        if task_request.task_type == "process_data":
            task_args = [task_request.data]
            task_kwargs = {"processing_type": task_request.options.get("processing_type", "default")} if task_request.options else {"processing_type": "default"}
            
        elif task_request.task_type == "send_notification":
            required_fields = ["recipient", "message"]
            for field in required_fields:
                if field not in task_request.data:
                    raise HTTPException(status_code=400, detail=f"Missing required field for notification: {field}")
            
            task_args = [task_request.data["recipient"], task_request.data["message"]]
            task_kwargs = {"notification_type": task_request.data.get("type", "email")}
            
        elif task_request.task_type == "health_check":
            task_args = []
            task_kwargs = {}
        else:
            # For other task types, use basic structure
            task_args = [task_request.data]
            task_kwargs = task_request.options or {}
        
        # Submit the task to Celery
        celery_task = celery_app.send_task(
            task_functions[task_request.task_type],
            args=task_args,
            kwargs=task_kwargs
        )

        await _persist_task(
            db,
            task_id=celery_task.id,
            name=task_request.task_type,
            function_name=task_functions[task_request.task_type],
            queue_name={
                "process_data": "data_processing",
                "send_notification": "notifications",
                "generate_report": "reports",
                "cleanup_data": "maintenance",
                "health_check": "default",
            }[task_request.task_type],
            payload={
                "data": task_request.data,
                "options": task_request.options or {},
                "task_type": task_request.task_type,
            },
            status="pending",
            metadata={
                "source": "submit_task",
                "task_type": task_request.task_type,
                "function_name": task_functions[task_request.task_type],
                "celery_task_id": celery_task.id,
            },
        )
        
        return TaskSubmissionResponse(
            task_id=celery_task.id,
            task_type=task_request.task_type,
            status="PENDING",
            submitted_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        raise HTTPException(status_code=500, detail=f"Task submission failed: {str(e)}")


@router.get("/status/{task_id}")
async def get_real_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Get the status of a submitted task."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get task status from Celery
        celery_task = celery_app.AsyncResult(task_id)

        row = await _fetch_task(db, task_id)
        
        response = {
            "task_id": task_id,
            "status": celery_task.status,
        }

        if row is not None:
            response["database_status"] = str(row["status"]).upper()
        
        if celery_task.successful():
            response["result"] = celery_task.result
        elif celery_task.failed():
            response["error"] = str(celery_task.info)
        elif celery_task.status == 'PROGRESS':
            response["progress"] = celery_task.info
            
        return response
        
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")
