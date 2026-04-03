"""
Custom logging utilities for InsightWeaver AI Engine
"""

import logging
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger


class TaskLogger:
    """Logger specifically for task-related operations."""

    def __init__(self, task_id: str, agent_name: Optional[str] = None):
        self.task_id = task_id
        self.agent_name = agent_name
        self.logger = logger.bind(task_id=task_id, agent=agent_name)

    def info(self, message: str, **kwargs):
        """Log info message with task context."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with task context."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with task context."""
        self.logger.error(message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with task context."""
        self.logger.debug(message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with task context."""
        self.logger.exception(message, **kwargs)


def setup_logging():
    """Setup logging configuration."""
    # Remove default logger
    logger.remove()

    # Add console handler
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        colorize=True
    )

    # Add file handler for errors
    logger.add(
        "logs/error.log",
        level="ERROR",
        rotation="10 MB",
        retention="7 days"
    )

    return logger


# Global logger instance
logger = setup_logging()


def get_task_logger(task_id: str, agent_name: Optional[str] = None) -> TaskLogger:
    """Get a task-specific logger."""
    return TaskLogger(task_id, agent_name)


def log_error(error: Exception, context: Dict[str, Any] = None):
    """Log an error with context."""
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.now().isoformat()
    }
    
    if context:
        error_data.update(context)
    
    logger.error(f"Error occurred: {str(error)}", **error_data)
