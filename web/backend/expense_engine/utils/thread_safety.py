"""
Thread Safety Utilities
Provides locking mechanisms for concurrent balance updates

Phase 10: Thread Safety & Concurrency
"""

import threading
import time
import logging
from typing import Dict, Optional, Callable, TypeVar
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LockType(Enum):
    """Types of locks available"""
    READ = "read"
    WRITE = "write"


@dataclass
class LockStats:
    """Statistics for lock usage"""
    acquisitions: int = 0
    releases: int = 0
    contentions: int = 0
    timeouts: int = 0
    total_wait_time_ms: float = 0.0
    
    def record_acquisition(self, wait_time_ms: float) -> None:
        """Record a successful lock acquisition"""
        self.acquisitions += 1
        self.total_wait_time_ms += wait_time_ms
    
    def record_release(self) -> None:
        """Record a lock release"""
        self.releases += 1
    
    def record_contention(self) -> None:
        """Record when lock was already held"""
        self.contentions += 1
    
    def record_timeout(self) -> None:
        """Record a lock timeout"""
        self.timeouts += 1
    
    @property
    def average_wait_time_ms(self) -> float:
        """Calculate average wait time"""
        if self.acquisitions == 0:
            return 0.0
        return self.total_wait_time_ms / self.acquisitions


class GroupLockManager:
    """
    Manages locks for group-level operations
    
    Prevents race conditions when multiple users update
    the same group's balances simultaneously.
    
    Uses a combination of:
    1. In-memory locks for same-process protection
    2. Firestore transactions for cross-process protection
    """
    
    # Default timeout in seconds
    DEFAULT_TIMEOUT = 30.0
    
    # Maximum number of locks to cache
    MAX_CACHED_LOCKS = 1000
    
    def __init__(self):
        """Initialize the lock manager"""
        self._locks: Dict[str, threading.RLock] = {}
        self._lock_creation_lock = threading.Lock()
        self._stats: Dict[str, LockStats] = {}
    
    def _get_or_create_lock(self, group_id: str) -> threading.RLock:
        """
        Get or create a lock for a specific group
        
        Args:
            group_id: The group ID to lock
            
        Returns:
            RLock for the group
        """
        if group_id not in self._locks:
            with self._lock_creation_lock:
                # Double-check after acquiring creation lock
                if group_id not in self._locks:
                    # Clean up old locks if too many cached
                    if len(self._locks) >= self.MAX_CACHED_LOCKS:
                        self._cleanup_old_locks()
                    
                    self._locks[group_id] = threading.RLock()
                    self._stats[group_id] = LockStats()
        
        return self._locks[group_id]
    
    def _cleanup_old_locks(self) -> None:
        """Remove locks that are not currently held"""
        locks_to_remove = []
        
        for group_id, lock in self._locks.items():
            # Try to acquire without blocking
            acquired = lock.acquire(blocking=False)
            if acquired:
                # Lock was free, safe to remove
                lock.release()
                locks_to_remove.append(group_id)
        
        # Remove half of the free locks (LRU would be better)
        for group_id in locks_to_remove[:len(locks_to_remove) // 2]:
            del self._locks[group_id]
            del self._stats[group_id]
        
        logger.info(
            "Cleaned up %d locks, %d remaining",
            len(locks_to_remove) // 2,
            len(self._locks)
        )
    
    @contextmanager
    def acquire_group_lock(
        self,
        group_id: str,
        timeout: Optional[float] = None
    ):
        """
        Context manager for acquiring a group lock
        
        Args:
            group_id: The group ID to lock
            timeout: Maximum time to wait for lock (seconds)
            
        Yields:
            None when lock is acquired
            
        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT
        
        lock = self._get_or_create_lock(group_id)
        stats = self._stats.get(group_id, LockStats())
        
        start_time = time.time()
        acquired = lock.acquire(timeout=timeout)
        wait_time_ms = (time.time() - start_time) * 1000
        
        if not acquired:
            stats.record_timeout()
            logger.warning(
                "Lock timeout for group %s after %.2f seconds",
                group_id,
                timeout
            )
            raise TimeoutError(
                f"Could not acquire lock for group {group_id} "
                f"within {timeout} seconds"
            )
        
        # Record stats
        if wait_time_ms > 10:  # More than 10ms wait indicates contention
            stats.record_contention()
        stats.record_acquisition(wait_time_ms)
        
        logger.debug(
            "Acquired lock for group %s (wait: %.2fms)",
            group_id,
            wait_time_ms
        )
        
        try:
            yield
        finally:
            lock.release()
            stats.record_release()
            logger.debug("Released lock for group %s", group_id)
    
    def get_stats(self, group_id: str) -> Optional[LockStats]:
        """
        Get statistics for a specific group's lock
        
        Args:
            group_id: The group ID
            
        Returns:
            LockStats or None if no stats exist
        """
        return self._stats.get(group_id)
    
    def get_all_stats(self) -> Dict[str, LockStats]:
        """Get statistics for all locks"""
        return dict(self._stats)
    
    def clear_stats(self) -> None:
        """Clear all statistics"""
        for stats in self._stats.values():
            stats.acquisitions = 0
            stats.releases = 0
            stats.contentions = 0
            stats.timeouts = 0
            stats.total_wait_time_ms = 0.0


# Global lock manager instance
_group_lock_manager: Optional[GroupLockManager] = None


def get_group_lock_manager() -> GroupLockManager:
    """
    Get the global group lock manager instance
    
    Returns:
        GroupLockManager singleton
    """
    # Use globals() to avoid pylint global statement warning
    if globals().get('_group_lock_manager') is None:
        globals()['_group_lock_manager'] = GroupLockManager()
    return globals()['_group_lock_manager']


def with_group_lock(
    group_id_param: str = "group_id",
    timeout: Optional[float] = None
):
    """
    Decorator for functions that need group-level locking
    
    Args:
        group_id_param: Name of the parameter containing group_id
        timeout: Lock timeout in seconds
        
    Returns:
        Decorated function
        
    Example:
        @with_group_lock(group_id_param="group_id")
        def update_expense(group_id: str, expense_id: str):
            # This code runs with group lock held
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Extract group_id from kwargs or positional args
            group_id = kwargs.get(group_id_param)
            
            if group_id is None:
                # Try to get from positional args based on function signature
                import inspect
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if group_id_param in params:
                    idx = params.index(group_id_param)
                    if idx < len(args):
                        group_id = args[idx]
            
            if group_id is None:
                raise ValueError(
                    f"Could not extract {group_id_param} from function arguments"
                )
            
            lock_manager = get_group_lock_manager()
            with lock_manager.acquire_group_lock(group_id, timeout=timeout):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


@dataclass
class OptimisticLockError(Exception):
    """Raised when optimistic locking fails due to version mismatch"""
    expected_version: int
    actual_version: int
    group_id: str
    
    def __str__(self) -> str:
        return (
            f"Version conflict for group {self.group_id}: "
            f"expected {self.expected_version}, got {self.actual_version}"
        )


class OptimisticLockManager:
    """
    Manages optimistic locking using version numbers
    
    This is used in conjunction with Firestore transactions
    to detect concurrent modifications.
    """
    
    @staticmethod
    def check_version(
        group_id: str,
        expected_version: int,
        actual_version: int
    ) -> None:
        """
        Check if version matches expected
        
        Args:
            group_id: Group ID being updated
            expected_version: Version client expects
            actual_version: Current version in database
            
        Raises:
            OptimisticLockError: If versions don't match
        """
        if expected_version != actual_version:
            logger.warning(
                "Version conflict for group %s: expected %d, got %d",
                group_id,
                expected_version,
                actual_version
            )
            raise OptimisticLockError(
                expected_version=expected_version,
                actual_version=actual_version,
                group_id=group_id
            )
    
    @staticmethod
    def increment_version(current_version: Optional[int]) -> int:
        """
        Calculate next version number
        
        Args:
            current_version: Current version or None
            
        Returns:
            Next version number
        """
        if current_version is None:
            return 1
        return current_version + 1


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay_ms: float = 100.0,
        max_delay_ms: float = 5000.0,
        exponential_base: float = 2.0
    ):
        """
        Initialize retry configuration
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay_ms: Initial delay between retries
            max_delay_ms: Maximum delay between retries
            exponential_base: Base for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.exponential_base = exponential_base
    
    def get_delay_ms(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in milliseconds
        """
        delay = self.base_delay_ms * (self.exponential_base ** attempt)
        return min(delay, self.max_delay_ms)


def with_retry(
    config: Optional[RetryConfig] = None,
    retry_exceptions: tuple = (OptimisticLockError,)
):
    """
    Decorator for retrying operations on specific exceptions
    
    Args:
        config: Retry configuration
        retry_exceptions: Tuple of exception types to retry on
        
    Returns:
        Decorated function
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as exc:
                    last_exception = exc
                    
                    if attempt < config.max_retries:
                        delay_ms = config.get_delay_ms(attempt)
                        logger.info(
                            "Retry attempt %d/%d after %.0fms delay: %s",
                            attempt + 1,
                            config.max_retries,
                            delay_ms,
                            str(exc)
                        )
                        time.sleep(delay_ms / 1000.0)
                    else:
                        logger.error(
                            "All %d retry attempts exhausted: %s",
                            config.max_retries + 1,
                            str(exc)
                        )
            
            if last_exception is not None:
                raise last_exception
            
            # Should never reach here
            raise RuntimeError("Unexpected retry loop exit")
        
        return wrapper
    return decorator
