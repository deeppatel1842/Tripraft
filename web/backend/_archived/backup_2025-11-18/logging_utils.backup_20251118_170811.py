"""
Production Logging Utilities
Environment-aware logging with data sanitization
"""

import os
import logging
import hashlib
import json
from typing import Any, Dict, Optional
from functools import wraps
from .production_config import LoggingConfig, SecurityConfig


# Determine if we're in production
IS_PRODUCTION = os.getenv('FLASK_ENV', 'development') == 'production'
IS_DEBUG = LoggingConfig.DEBUG_ENABLED


class ProductionLogger:
    """Production-safe logger with automatic data sanitization"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure logger based on environment"""
        level = getattr(logging, LoggingConfig.LOG_LEVEL.upper(), logging.INFO)
        self.logger.setLevel(level)
        
        if not self.logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            
            # Format
            if LoggingConfig.LOG_FORMAT == 'json':
                formatter = JsonFormatter()
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # File handler (if enabled)
            if LoggingConfig.LOG_TO_FILE:
                from logging.handlers import RotatingFileHandler
                os.makedirs(os.path.dirname(LoggingConfig.LOG_FILE_PATH), exist_ok=True)
                file_handler = RotatingFileHandler(
                    LoggingConfig.LOG_FILE_PATH,
                    maxBytes=LoggingConfig.LOG_MAX_BYTES,
                    backupCount=LoggingConfig.LOG_BACKUP_COUNT
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
    
    @staticmethod
    def sanitize_data(data: Any, depth: int = 0) -> Any:
        """Recursively sanitize sensitive data"""
        if depth > 5:  # Prevent infinite recursion
            return "[MAX_DEPTH]"
        
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = key.lower()
                
                # Check if key is sensitive
                is_sensitive = any(
                    sensitive in key_lower 
                    for sensitive in SecurityConfig.SENSITIVE_FIELDS
                )
                
                if is_sensitive:
                    sanitized[key] = "[REDACTED]"
                elif key_lower in ['user_id', 'uid', 'invited_by', 'created_by', 'paid_by']:
                    # Hash user IDs
                    sanitized[key] = ProductionLogger.hash_id(str(value))
                elif key_lower == 'email':
                    # Mask email
                    sanitized[key] = ProductionLogger.mask_email(str(value))
                else:
                    sanitized[key] = ProductionLogger.sanitize_data(value, depth + 1)
            return sanitized
        
        elif isinstance(data, (list, tuple)):
            return [ProductionLogger.sanitize_data(item, depth + 1) for item in data]
        
        else:
            return data
    
    @staticmethod
    def hash_id(user_id: str) -> str:
        """Hash user ID for logging (show prefix only)"""
        if not user_id:
            return "[EMPTY]"
        
        if IS_DEBUG:
            return user_id  # Show full ID in debug mode
        
        # Show first 8 chars + hash of rest
        prefix = user_id[:SecurityConfig.LOG_USER_ID_PREFIX_LENGTH]
        hash_suffix = hashlib.sha256(user_id.encode()).hexdigest()[:8]
        return f"{prefix}***{hash_suffix}"
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email address"""
        if not email or '@' not in email:
            return "[INVALID_EMAIL]"
        
        if IS_DEBUG:
            return email  # Show full email in debug mode
        
        if not SecurityConfig.MASK_EMAIL_DOMAIN:
            return email
        
        local, domain = email.split('@')
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1] if len(local) > 2 else local
        return f"{masked_local}@{domain}"
    
    def info(self, msg: str, data: Optional[Dict] = None, **kwargs):
        """Log info message with sanitized data"""
        if IS_PRODUCTION and not LoggingConfig.LOG_USER_ACTIONS:
            return
        
        if data:
            sanitized = self.sanitize_data(data)
            self.logger.info(f"{msg} | Data: {sanitized}", **kwargs)
        else:
            self.logger.info(msg, **kwargs)
    
    def debug(self, msg: str, data: Optional[Dict] = None, **kwargs):
        """Log debug message (only if debug enabled)"""
        if not IS_DEBUG:
            return
        
        if data:
            sanitized = self.sanitize_data(data)
            self.logger.debug(f"{msg} | Data: {sanitized}", **kwargs)
        else:
            self.logger.debug(msg, **kwargs)
    
    def warning(self, msg: str, data: Optional[Dict] = None, **kwargs):
        """Log warning message"""
        if data:
            sanitized = self.sanitize_data(data)
            self.logger.warning(f"{msg} | Data: {sanitized}", **kwargs)
        else:
            self.logger.warning(msg, **kwargs)
    
    def error(self, msg: str, error: Optional[Exception] = None, data: Optional[Dict] = None, **kwargs):
        """Log error message with sanitized context"""
        error_msg = msg
        
        if error:
            if SecurityConfig.SANITIZE_ERROR_MESSAGES:
                error_msg += f" | Error: {type(error).__name__}"
            else:
                error_msg += f" | Error: {str(error)}"
        
        if data:
            sanitized = self.sanitize_data(data)
            self.logger.error(f"{error_msg} | Data: {sanitized}", **kwargs)
        else:
            self.logger.error(error_msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """Log critical message"""
        self.logger.critical(msg, **kwargs)
    
    def performance(self, operation: str, duration_ms: float, metadata: Optional[Dict] = None):
        """Log performance metrics"""
        if not LoggingConfig.LOG_PERFORMANCE_METRICS:
            return
        
        msg = f"PERFORMANCE | {operation} | {duration_ms:.2f}ms"
        
        if metadata:
            sanitized = self.sanitize_data(metadata)
            msg += f" | {sanitized}"
        
        self.logger.info(msg)
    
    def cache_hit(self, cache_type: str, key: str):
        """Log cache hit"""
        if not LoggingConfig.LOG_CACHE_HITS:
            return
        
        hashed_key = self.hash_id(key)
        self.logger.debug(f"CACHE HIT | {cache_type} | {hashed_key}")
    
    def cache_miss(self, cache_type: str, key: str):
        """Log cache miss"""
        if not LoggingConfig.LOG_CACHE_HITS:
            return
        
        hashed_key = self.hash_id(key)
        self.logger.debug(f"CACHE MISS | {cache_type} | {hashed_key}")
    
    def firestore_op(self, op_type: str, collection: str, count: int = 1):
        """Log Firestore operation"""
        if not LoggingConfig.LOG_FIRESTORE_OPS:
            return
        
        self.logger.debug(f"FIRESTORE | {op_type} | {collection} | count={count}")


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def log_execution_time(func):
    """Decorator to log function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not LoggingConfig.LOG_PERFORMANCE_METRICS:
            return func(*args, **kwargs)
        
        import time
        start = time.time()
        result = func(*args, **kwargs)
        duration_ms = (time.time() - start) * 1000
        
        logger = ProductionLogger(func.__module__)
        logger.performance(f"{func.__name__}", duration_ms)
        
        return result
    return wrapper


def sample_debug_log(sample_rate: float = None):
    """Decorator to sample debug logs (reduce volume in production)"""
    if sample_rate is None:
        sample_rate = LoggingConfig.DEBUG_SAMPLE_RATE
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import random
            if random.random() < sample_rate or IS_DEBUG:
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Create default logger instance
def get_logger(name: str) -> ProductionLogger:
    """Get a production-safe logger instance"""
    return ProductionLogger(name)


# Convenience function for existing code
def create_logger(name: str) -> ProductionLogger:
    """Alias for get_logger"""
    return get_logger(name)
