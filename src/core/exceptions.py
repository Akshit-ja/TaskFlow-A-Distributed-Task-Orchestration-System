"""
Custom exceptions for the distributed task queue system.
"""

from typing import Any, Dict, Optional


class TaskQueueException(Exception):
    """Base exception for task queue system."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize exception.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class TaskNotFoundError(TaskQueueException):
    """Raised when a task is not found."""
    
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task with ID '{task_id}' not found",
            status_code=404,
            error_code="TASK_NOT_FOUND",
            details={"task_id": task_id}
        )


class TaskValidationError(TaskQueueException):
    """Raised when task validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="TASK_VALIDATION_ERROR",
            details=details or {}
        )


class QueueNotFoundError(TaskQueueException):
    """Raised when a queue is not found."""
    
    def __init__(self, queue_name: str):
        super().__init__(
            message=f"Queue '{queue_name}' not found",
            status_code=404,
            error_code="QUEUE_NOT_FOUND",
            details={"queue_name": queue_name}
        )


class WorkerError(TaskQueueException):
    """Raised when a worker encounters an error."""
    
    def __init__(self, message: str, worker_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="WORKER_ERROR",
            details={
                "worker_id": worker_id,
                **(details or {})
            }
        )


class TaskExecutionError(TaskQueueException):
    """Raised when task execution fails."""
    
    def __init__(
        self,
        task_id: str,
        task_name: str,
        original_error: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Task '{task_name}' (ID: {task_id}) execution failed: {original_error}",
            status_code=500,
            error_code="TASK_EXECUTION_ERROR",
            details={
                "task_id": task_id,
                "task_name": task_name,
                "original_error": original_error,
                **(details or {})
            }
        )


class TaskTimeoutError(TaskQueueException):
    """Raised when a task execution times out."""
    
    def __init__(self, task_id: str, timeout_seconds: int):
        super().__init__(
            message=f"Task with ID '{task_id}' timed out after {timeout_seconds} seconds",
            status_code=408,
            error_code="TASK_TIMEOUT",
            details={
                "task_id": task_id,
                "timeout_seconds": timeout_seconds
            }
        )


class DatabaseError(TaskQueueException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Database operation '{operation}' failed: {message}",
            status_code=500,
            error_code="DATABASE_ERROR",
            details={
                "operation": operation,
                **(details or {})
            }
        )


class RedisError(TaskQueueException):
    """Raised when Redis operations fail."""
    
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Redis operation '{operation}' failed: {message}",
            status_code=500,
            error_code="REDIS_ERROR",
            details={
                "operation": operation,
                **(details or {})
            }
        )


class ConfigurationError(TaskQueueException):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, config_key: str):
        super().__init__(
            message=f"Configuration error for '{config_key}': {message}",
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key}
        )


class AuthenticationError(TaskQueueException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(TaskQueueException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR"
        )


class RateLimitError(TaskQueueException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after} if retry_after else {}
        )