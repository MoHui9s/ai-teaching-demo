"""Logging configuration for Hermes Agent."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(
    log_level: str = "INFO",
    log_file: bool = True,
    log_dir: Path = Path("logs"),
    log_to_console: bool = True
) -> logging.Logger:
    """
    Configure structured logging with file and console output.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Whether to log to file
        log_dir: Directory for log files
        log_to_console: Whether to log to console

    Returns:
        Configured logger instance
    """
    # Create logs directory
    if log_file:
        log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger("hermes")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        # Daily log file: logs/hermes-2024-01-15.log
        log_filename = log_dir / f"hermes-{datetime.now().strftime('%Y-%m-%d')}.log"

        file_handler = RotatingFileHandler(
            log_filename,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "hermes") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


# Initialize default logger
DEFAULT_LOGGER = setup_logging()


def log_request(logger: logging.Logger, method: str, url: str, **kwargs):
    """Log API request with structured format."""
    logger.info(f"API Request | {method} {url}")
    for key, value in kwargs.items():
        logger.debug(f"  {key}: {value}")


def log_response(logger: logging.Logger, status: int, **kwargs):
    """Log API response with structured format."""
    logger.info(f"API Response | Status: {status}")
    for key, value in kwargs.items():
        logger.debug(f"  {key}: {value}")


def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """Log error with context."""
    logger.error(f"Error{' in ' + context if context else ''}: {type(error).__name__}: {error}")


def log_user_action(logger: logging.Logger, user_id: str, action: str, **kwargs):
    """Log user action."""
    logger.info(f"User Action | user_id={user_id} | {action}")
    for key, value in kwargs.items():
        logger.debug(f"  {key}: {value}")


def log_tool_call(logger: logging.Logger, tool: str, action: str, **kwargs):
    """Log tool call."""
    logger.info(f"Tool Call | {tool} | {action}")
    for key, value in kwargs.items():
        logger.debug(f"  {key}: {value}")
