"""
Celery application setup for the distributed task queue system.

This module configures Celery with Redis as the broker and result backend,
integrates with the PostgreSQL database, and sets up task routing and monitoring.
"""

import logging
from celery import Celery
from celery.signals import (
    task_prerun, task_postrun, task_failure, task_success, 
    worker_ready, worker_shutting_down
)

from src.core.config import get_settings, get_celery_config
from src.core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Get application settings
settings = get_settings()
celery_config = get_celery_config()

# Create Celery application instance
app = Celery(
    'distributed_task_queue',
    broker=celery_config['broker_url'],
    backend=celery_config['result_backend'],
    include=[
        'src.worker.tasks',
        'src.worker.scheduled_tasks',
    ]
)

# Configure Celery with settings
app.conf.update(celery_config)

# Additional Celery configuration
app.conf.update(
    # Task execution settings
    task_always_eager=False,  # Set to True for testing/development
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_eager_result=True,
    
    # Task routing and queues
    task_default_queue='default',
    task_default_exchange='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=settings.WORKER_MAX_TASKS_PER_CHILD,
    worker_disable_rate_limits=False,
    
    # Monitoring and visibility
    task_send_events=True,
    worker_send_task_events=True,
    task_track_started=True,
    task_acks_late=True,
    worker_hijack_root_logger=False,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Security settings (configure for production)
    worker_enable_remote_control=True,
    
    # Beat scheduler settings (for periodic tasks)
    beat_scheduler='celery.beat:PersistentScheduler',
    beat_schedule_filename='celerybeat-schedule',
    
    # Time zone settings
    timezone='UTC',
    enable_utc=True,
)

# Queue definitions
app.conf.task_routes = {
    'src.worker.tasks.process_data': {'queue': 'data_processing'},
    'src.worker.tasks.send_notification': {'queue': 'notifications'},
    'src.worker.tasks.generate_report': {'queue': 'reports'},
    'src.worker.tasks.cleanup_old_data': {'queue': 'maintenance'},
    'src.worker.scheduled_tasks.*': {'queue': 'scheduled'},
}


# Signal handlers for monitoring and logging
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task pre-execution."""
    logger.info(f"Task {task.name}[{task_id}] starting with args={args}, kwargs={kwargs}")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task post-execution."""
    logger.info(f"Task {task.name}[{task_id}] completed with state={state}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failures."""
    logger.error(f"Task {sender.name}[{task_id}] failed: {exception}")
    logger.debug(f"Task failure traceback: {traceback}")


@task_success.connect
def task_success_handler(sender=None, result=None, **kwds):
    """Handle successful task completion."""
    logger.info(f"Task {sender.name} completed successfully")


@worker_ready.connect
def worker_ready_handler(sender, **kwargs):
    """Handle worker ready signal."""
    logger.info(f"Worker {sender.hostname} is ready to process tasks")


@worker_shutting_down.connect
def worker_shutting_down_handler(sender, **kwargs):
    """Handle worker shutdown signal."""
    logger.info(f"Worker {sender.hostname} is shutting down")


# Health check task
@app.task(bind=True, name='health_check')
def health_check_task(self):
    """Simple health check task for monitoring worker availability."""
    return {
        'status': 'healthy',
        'worker_id': self.request.id,
        'timestamp': self.request.utcoffset or 'unknown'
    }


if __name__ == '__main__':
    app.start()