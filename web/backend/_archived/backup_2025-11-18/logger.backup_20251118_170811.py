"""
Professional logging configuration for Group Planner
Supports environment-based log levels and proper formatting
"""
import logging
import sys
from typing import Optional
from .constants import GroupPlannerConfig

# Define color codes for console output (optional)
class LogColors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    DEBUG = '\033[36m'  # Cyan
    INFO = '\033[32m'   # Green
    WARNING = '\033[33m'  # Yellow
    ERROR = '\033[31m'  # Red
    CRITICAL = '\033[35m'  # Magenta


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support"""
    
    COLORS = {
        logging.DEBUG: LogColors.DEBUG,
        logging.INFO: LogColors.INFO,
        logging.WARNING: LogColors.WARNING,
        logging.ERROR: LogColors.ERROR,
        logging.CRITICAL: LogColors.CRITICAL,
    }
    
    def format(self, record):
        if sys.stdout.isatty():  # Only use colors if output is a terminal
            color = self.COLORS.get(record.levelno, LogColors.RESET)
            record.levelname = f"{color}{record.levelname}{LogColors.RESET}"
        return super().format(record)


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance
    
    Args:
        name: Logger name (usually __name__)
        level: Log level override (DEBUG, INFO, WARN, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        # >>> logger.info("User %s created group %s", user_id, group_id)
    """
    logger = logging.getLogger(name)
    
    # Set level from config or parameter
    log_level = level or GroupPlannerConfig.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    # Format: [2025-11-14 10:30:45] INFO in routes: Token verified
    formatter = ColoredFormatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Don't propagate to root logger
    logger.propagate = False
    
    return logger


def configure_logging():
    """
    Configure root logging for the application
    Call this once at application startup
    """
    log_level = GroupPlannerConfig.LOG_LEVEL
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Suppress noisy loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('firebase_admin').setLevel(logging.WARNING)


# Convenience function for debug mode only logging
def debug_log(logger: logging.Logger, message: str, *args):
    """
    Log only if debug logging is enabled
    
    Args:
        logger: Logger instance
        message: Message to log
        *args: Arguments for lazy string formatting
    """
    if GroupPlannerConfig.DEBUG_LOGGING:
        # logger.debug(message, *args)
