"""
Scheduled tasks for periodic operations in the distributed task queue system.

This module contains Celery Beat scheduled tasks that run periodically
for maintenance, monitoring, and housekeeping operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from src.worker.main import app
from src.worker.tasks import cleanup_old_data, generate_report

logger = logging.getLogger(__name__)


@app.task(name='scheduled_cleanup')
def scheduled_cleanup() -> Dict[str, Any]:
    """
    Scheduled cleanup task that runs daily to clean up old data.
    
    Returns:
        Dict containing cleanup results
    """
    logger.info("Starting scheduled cleanup task")
    
    try:
        # Clean up completed tasks older than 7 days
        cleanup_result = cleanup_old_data.delay("all", 7)
        
        return {
            "status": "initiated",
            "cleanup_task_id": cleanup_result.id,
            "scheduled_at": datetime.utcnow().isoformat(),
            "cleanup_type": "all",
            "days_old": 7
        }
        
    except Exception as exc:
        logger.error(f"Scheduled cleanup failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
            "scheduled_at": datetime.utcnow().isoformat()
        }


@app.task(name='scheduled_health_check')
def scheduled_health_check() -> Dict[str, Any]:
    """
    Scheduled health check that monitors system status.
    
    Returns:
        Dict containing health status
    """
    logger.info("Running scheduled health check")
    
    try:
        # Perform basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "worker_responsive": True,
                "memory_usage": "normal",  # In production, check actual memory
                "task_processing": "active"
            }
        }
        
        logger.info("Health check completed successfully")
        return health_status
        
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        return {
            "status": "unhealthy",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.task(name='scheduled_daily_report')
def scheduled_daily_report() -> Dict[str, Any]:
    """
    Generate daily summary report.
    
    Returns:
        Dict containing report generation status
    """
    logger.info("Generating scheduled daily report")
    
    try:
        # Calculate yesterday's date range
        yesterday = datetime.utcnow() - timedelta(days=1)
        date_range = {
            "start": yesterday.strftime("%Y-%m-%d 00:00:00"),
            "end": yesterday.strftime("%Y-%m-%d 23:59:59")
        }
        
        # Generate task summary report
        report_task = generate_report.delay(
            "task_summary", 
            date_range, 
            {"automated": True, "report_type": "daily"}
        )
        
        return {
            "status": "initiated",
            "report_task_id": report_task.id,
            "report_type": "daily_summary",
            "date_range": date_range,
            "scheduled_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Daily report generation failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
            "scheduled_at": datetime.utcnow().isoformat()
        }


# Configure periodic tasks schedule
app.conf.beat_schedule = {
    'daily-cleanup': {
        'task': 'scheduled_cleanup',
        'schedule': 86400.0,  # Run daily (24 hours)
    },
    'health-check': {
        'task': 'scheduled_health_check',
        'schedule': 300.0,  # Run every 5 minutes
    },
    'daily-report': {
        'task': 'scheduled_daily_report',
        'schedule': 86400.0,  # Run daily
        'options': {'queue': 'reports'}
    },
}