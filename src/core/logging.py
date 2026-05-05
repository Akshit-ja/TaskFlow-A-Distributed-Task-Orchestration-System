"""
Logging configuration and setup.
"""

import os
import sys
import logging
import logging.config
from pathlib import Path

from src.core.config import get_settings


def setup_logging():
    """
    Setup application logging configuration.
    """
    settings = get_settings()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Use external logging.ini if it exists, otherwise use default config
    if os.path.exists("logging.ini"):
        logging.config.fileConfig("logging.ini")
        return
    
    # Default logging configuration
    log_format = {
        "standard": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        "detailed": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(funcName)s(): %(message)s",
        "json": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}',
    }
    
    formatter = logging.Formatter(
        log_format.get(settings.LOG_FORMAT, log_format["standard"])
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        "logs/error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    loggers_config = {
        "uvicorn": logging.INFO,
        "fastapi": logging.INFO,
        "sqlalchemy.engine": logging.WARNING,
        "celery": logging.INFO,
        "src": getattr(logging, settings.LOG_LEVEL),
    }
    
    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.propagate = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)