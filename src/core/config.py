"""
Application configuration management using Pydantic settings.
"""

import os
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost:5432/task_queue",
        description="PostgreSQL database URL"
    )
    DATABASE_URL_ASYNC: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/task_queue",
        description="Async PostgreSQL database URL"
    )
    
    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", description="API server host")
    API_PORT: int = Field(default=8000, description="API server port")
    API_WORKERS: int = Field(default=4, description="Number of API worker processes")
    API_RELOAD: bool = Field(default=True, description="Enable auto-reload for development")
    
    # Worker Configuration
    WORKER_CONCURRENCY: int = Field(default=4, description="Number of worker processes")
    WORKER_HEARTBEAT_INTERVAL: int = Field(default=30, description="Worker heartbeat interval in seconds")
    WORKER_MAX_TASKS_PER_CHILD: int = Field(default=1000, description="Max tasks per worker child process")
    
    # Security Configuration
    SECRET_KEY: str = Field(
        default="your-secret-key-here-please-change-in-production",
        description="Secret key for JWT tokens"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT token expiration time")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="standard", description="Logging format (standard, json)")
    
    # Task Configuration
    DEFAULT_TASK_TIMEOUT: int = Field(default=300, description="Default task timeout in seconds")
    MAX_RETRY_ATTEMPTS: int = Field(default=3, description="Maximum retry attempts for failed tasks")
    RETRY_BACKOFF_SECONDS: int = Field(default=60, description="Retry backoff delay in seconds")
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")
    METRICS_PORT: int = Field(default=9090, description="Metrics server port")
    
    # Celery Configuration
    CELERY_BROKER_URL: Optional[str] = Field(default=None, description="Celery broker URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, description="Celery result backend URL")
    
    @model_validator(mode='before')
    @classmethod
    def set_celery_broker_url(cls, values):
        """Set Celery broker URL from Redis URL if not provided."""
        if isinstance(values, dict):
            if values.get("CELERY_BROKER_URL") is None:
                values["CELERY_BROKER_URL"] = values.get("REDIS_URL", "redis://localhost:6379/0")
        return values
    
    @model_validator(mode='before')
    @classmethod
    def set_celery_result_backend(cls, values):
        """Set Celery result backend URL from Redis URL if not provided."""
        if isinstance(values, dict):
            if values.get("CELERY_RESULT_BACKEND") is None:
                values["CELERY_RESULT_BACKEND"] = values.get("REDIS_URL", "redis://localhost:6379/0")
        return values
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @field_validator("LOG_FORMAT")
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = ["standard", "json", "detailed"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Log format must be one of: {valid_formats}")
        return v.lower()
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings
    """
    return Settings()


def get_database_url(async_db: bool = False) -> str:
    """
    Get database URL based on sync/async requirement.
    
    Args:
        async_db: Whether to return async database URL
        
    Returns:
        str: Database connection URL
    """
    settings = get_settings()
    return settings.DATABASE_URL_ASYNC if async_db else settings.DATABASE_URL


def get_redis_config() -> dict:
    """
    Get Redis configuration dictionary.
    
    Returns:
        dict: Redis connection configuration
    """
    settings = get_settings()
    return {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "url": settings.REDIS_URL,
    }


def get_celery_config() -> dict:
    """
    Get Celery configuration dictionary.
    
    Returns:
        dict: Celery configuration
    """
    settings = get_settings()
    return {
        "broker_url": settings.CELERY_BROKER_URL,
        "result_backend": settings.CELERY_RESULT_BACKEND,
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
        "worker_hijack_root_logger": False,
        "worker_concurrency": settings.WORKER_CONCURRENCY,
        "worker_max_tasks_per_child": settings.WORKER_MAX_TASKS_PER_CHILD,
        "beat_schedule": {},
        "task_routes": {
            "src.worker.tasks.*": {"queue": "default"},
        },
    }