"""
Task definitions for the distributed task queue system.

This module contains Celery tasks that demonstrate various types of background processing
including data processing, notifications, reporting, and database operations.
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4

from celery import Task
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.worker.main import app
from src.core.database import AsyncSessionLocal, get_async_db
from src.core.redis_client import get_redis
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseTask(Task):
    """Base task class that provides database session management."""
    
    def __init__(self):
        self._session = None
    
    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            self._session = AsyncSessionLocal()
        return self._session
    
    def after_return(self, *args, **kwargs):
        if self._session:
            self._session.close()


# Data Processing Tasks
@app.task(bind=True, base=DatabaseTask, name='process_data')
def process_data(self, data: Dict[str, Any], processing_type: str = "default") -> Dict[str, Any]:
    """
    Process incoming data with specified processing type.
    
    Args:
        data: The data to process
        processing_type: Type of processing to perform
        
    Returns:
        Dict containing processing results
    """
    task_id = self.request.id
    logger.info(f"Starting data processing task {task_id} with type: {processing_type}")
    
    start_time = time.time()
    
    try:
        # Simulate different processing types
        if processing_type == "transform":
            result = _transform_data(data)
        elif processing_type == "validate":
            result = _validate_data(data)
        elif processing_type == "enrich":
            result = _enrich_data(data)
        else:
            result = _default_processing(data)
        
        processing_time = time.time() - start_time
        
        # Store processing statistics in database
        _store_task_stats(task_id, "process_data", processing_time, "success")
        
        logger.info(f"Data processing task {task_id} completed in {processing_time:.2f} seconds")
        
        return {
            "task_id": task_id,
            "status": "completed",
            "processing_type": processing_type,
            "processing_time": processing_time,
            "input_size": len(str(data)),
            "output_size": len(str(result)),
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        processing_time = time.time() - start_time
        _store_task_stats(task_id, "process_data", processing_time, "failed")
        
        logger.error(f"Data processing task {task_id} failed: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@app.task(bind=True, name='send_notification')
def send_notification(self, recipient: str, message: str, notification_type: str = "email") -> Dict[str, Any]:
    """
    Send notification to recipient.
    
    Args:
        recipient: Notification recipient
        message: Message content
        notification_type: Type of notification (email, sms, push)
        
    Returns:
        Dict containing delivery status
    """
    task_id = self.request.id
    logger.info(f"Sending {notification_type} notification to {recipient}")
    
    try:
        # Simulate notification sending
        delivery_time = _simulate_notification_delivery(notification_type)
        time.sleep(delivery_time)
        
        # Store notification record
        notification_record = {
            "id": str(uuid4()),
            "task_id": task_id,
            "recipient": recipient,
            "message": message,
            "type": notification_type,
            "status": "delivered",
            "sent_at": datetime.utcnow().isoformat(),
            "delivery_time": delivery_time
        }
        
        # Cache notification for quick lookup
        _cache_notification_record(notification_record)
        
        logger.info(f"Notification sent successfully to {recipient}")
        
        return {
            "task_id": task_id,
            "status": "delivered",
            "recipient": recipient,
            "type": notification_type,
            "delivery_time": delivery_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to send notification: {exc}")
        raise self.retry(exc=exc, countdown=30, max_retries=5)


@app.task(bind=True, base=DatabaseTask, name='generate_report')
def generate_report(self, report_type: str, date_range: Dict[str, str], filters: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Generate various types of reports.
    
    Args:
        report_type: Type of report to generate
        date_range: Date range for the report
        filters: Additional filters to apply
        
    Returns:
        Dict containing report data and metadata
    """
    task_id = self.request.id
    logger.info(f"Generating {report_type} report for range {date_range}")
    
    start_time = time.time()
    
    try:
        # Simulate report generation based on type
        if report_type == "task_summary":
            report_data = _generate_task_summary_report(date_range, filters)
        elif report_type == "performance":
            report_data = _generate_performance_report(date_range, filters)
        elif report_type == "error_analysis":
            report_data = _generate_error_analysis_report(date_range, filters)
        else:
            report_data = _generate_default_report(date_range, filters)
        
        generation_time = time.time() - start_time
        
        # Store report metadata in database
        report_record = {
            "id": str(uuid4()),
            "task_id": task_id,
            "type": report_type,
            "date_range": date_range,
            "filters": filters or {},
            "record_count": len(report_data.get("data", [])),
            "generation_time": generation_time,
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Report generation completed in {generation_time:.2f} seconds")
        
        return {
            "task_id": task_id,
            "status": "completed",
            "report_type": report_type,
            "metadata": report_record,
            "data": report_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}")
        raise self.retry(exc=exc, countdown=120, max_retries=2)


@app.task(bind=True, base=DatabaseTask, name='cleanup_old_data')
def cleanup_old_data(self, cleanup_type: str = "all", days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old data from the database.
    
    Args:
        cleanup_type: Type of cleanup to perform
        days_old: Age threshold for cleanup
        
    Returns:
        Dict containing cleanup statistics
    """
    task_id = self.request.id
    logger.info(f"Starting {cleanup_type} cleanup for data older than {days_old} days")
    
    try:
        cleanup_stats = {}
        
        if cleanup_type in ["all", "completed_tasks"]:
            completed_deleted = _cleanup_completed_tasks(days_old)
            cleanup_stats["completed_tasks"] = completed_deleted
        
        if cleanup_type in ["all", "logs"]:
            logs_deleted = _cleanup_old_logs(days_old)
            cleanup_stats["logs"] = logs_deleted
        
        if cleanup_type in ["all", "cache"]:
            cache_cleared = _cleanup_cache()
            cleanup_stats["cache_entries"] = cache_cleared
        
        total_cleaned = sum(cleanup_stats.values())
        
        logger.info(f"Cleanup completed. Total items cleaned: {total_cleaned}")
        
        return {
            "task_id": task_id,
            "status": "completed",
            "cleanup_type": cleanup_type,
            "days_old": days_old,
            "statistics": cleanup_stats,
            "total_cleaned": total_cleaned,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}")
        raise


# Helper Functions
def _transform_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform data according to business rules."""
    # Simulate data transformation
    transformed = {
        "original": data,
        "transformed": {k: str(v).upper() if isinstance(v, str) else v for k, v in data.items()},
        "transformation_applied": "uppercase_strings",
        "processed_at": datetime.utcnow().isoformat()
    }
    time.sleep(0.5)  # Simulate processing time
    return transformed


def _validate_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate data against predefined rules."""
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Example validation rules
    required_fields = ["id", "name"]
    for field in required_fields:
        if field not in data:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Missing required field: {field}")
    
    time.sleep(0.3)  # Simulate validation time
    return {"validation": validation_results, "data": data}


def _enrich_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich data with additional information."""
    enriched = data.copy()
    enriched.update({
        "enrichment_timestamp": datetime.utcnow().isoformat(),
        "enrichment_source": "internal_api",
        "metadata": {
            "processed": True,
            "enrichment_version": "1.0"
        }
    })
    time.sleep(0.7)  # Simulate enrichment time
    return enriched


def _default_processing(data: Dict[str, Any]) -> Dict[str, Any]:
    """Default data processing."""
    return {
        "processed_data": data,
        "processing_type": "default",
        "processed_at": datetime.utcnow().isoformat()
    }


def _simulate_notification_delivery(notification_type: str) -> float:
    """Simulate notification delivery time based on type."""
    delivery_times = {
        "email": 0.5,
        "sms": 0.3,
        "push": 0.1,
        "webhook": 0.2
    }
    return delivery_times.get(notification_type, 0.5)


async def _cache_notification_record(record: Dict[str, Any]):
    """Cache notification record in Redis."""
    try:
        redis_client = await get_redis()
        await redis_client.set_json(f"notification:{record['id']}", record, expire=86400)
    except Exception as e:
        logger.warning(f"Failed to cache notification record: {e}")


def _store_task_stats(task_id: str, task_name: str, processing_time: float, status: str):
    """Store task execution statistics."""
    # In a real implementation, this would insert into the database
    stats = {
        "task_id": task_id,
        "task_name": task_name,
        "processing_time": processing_time,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info(f"Task stats: {stats}")


def _generate_task_summary_report(date_range: Dict[str, str], filters: Optional[Dict]) -> Dict[str, Any]:
    """Generate task summary report."""
    # Simulate report data
    return {
        "summary": {
            "total_tasks": 150,
            "completed": 120,
            "failed": 20,
            "pending": 10
        },
        "data": [
            {"date": "2024-01-01", "completed": 45, "failed": 5},
            {"date": "2024-01-02", "completed": 52, "failed": 3},
            {"date": "2024-01-03", "completed": 38, "failed": 7}
        ]
    }


def _generate_performance_report(date_range: Dict[str, str], filters: Optional[Dict]) -> Dict[str, Any]:
    """Generate performance report."""
    return {
        "metrics": {
            "avg_processing_time": 2.5,
            "throughput_per_hour": 75,
            "success_rate": 0.92
        },
        "data": []
    }


def _generate_error_analysis_report(date_range: Dict[str, str], filters: Optional[Dict]) -> Dict[str, Any]:
    """Generate error analysis report."""
    return {
        "error_summary": {
            "total_errors": 25,
            "error_rate": 0.08,
            "most_common": "Connection timeout"
        },
        "data": []
    }


def _generate_default_report(date_range: Dict[str, str], filters: Optional[Dict]) -> Dict[str, Any]:
    """Generate default report."""
    return {"message": "Default report generated", "data": []}


def _cleanup_completed_tasks(days_old: int) -> int:
    """Clean up completed tasks older than specified days."""
    # Simulate cleanup
    time.sleep(1.0)
    return 45  # Simulated number of tasks cleaned


def _cleanup_old_logs(days_old: int) -> int:
    """Clean up old log entries."""
    time.sleep(0.5)
    return 120  # Simulated number of log entries cleaned


async def _cleanup_cache() -> int:
    """Clean up old cache entries."""
    try:
        redis_client = await get_redis()
        # Simulate cache cleanup
        return 25  # Simulated number of cache entries cleaned
    except Exception:
        return 0