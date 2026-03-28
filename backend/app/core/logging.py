"""
Sumatic Modern IoT - Logging Configuration
Structured logging configuration for the application.
"""
import logging
import sys
from typing import Any

from loguru import logger as loguru_logger

from app.config import get_settings

settings = get_settings()


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and redirect to Loguru.
    This allows us to use Loguru for all logging while maintaining
    compatibility with third-party libraries that use standard logging.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to Loguru."""
        # Get corresponding Loguru level if it exists
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """
    Configure application logging with Loguru.
    """
    # Remove default handler
    loguru_logger.remove()

    # Add console handler with format
    # Use stderr on Windows to avoid hot-reload issues with stdout
    import platform
    console_stream = sys.stderr if platform.system() == "Windows" else sys.stdout
    
    loguru_logger.add(
        console_stream,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
        backtrace=True,
        diagnose=True,
        catch=True,  # Catch errors to prevent crashes during hot-reload
    )

    # Add file handler for errors
    loguru_logger.add(
        "logs/error.log",
        rotation="1 day",
        retention="30 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        backtrace=True,
        diagnose=True,
    )

    # Add file handler for all logs
    loguru_logger.add(
        "logs/app.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG" if settings.DEBUG else "INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        backtrace=True,
        diagnose=True,
    )

    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


def get_logger(name: str):
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return loguru_logger.bind(name=name)
