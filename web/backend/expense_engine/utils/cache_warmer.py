"""
Cache Warmer - Startup Cache Population
Pre-loads frequently accessed data into cache on startup

Phase 5: Performance Optimization
"""

import logging
import threading
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)


class CacheWarmerTask:
    """Represents a cache warming task"""
    
    def __init__(
        self,
        name: str,
        fetch_func: Callable[[], Any],
        cache_key: str,
        ttl: int = 300,
        priority: int = 1,
        enabled: bool = True
    ):
        """
        Initialize cache warmer task
        
        Args:
            name: Task name for logging
            fetch_func: Function to fetch data
            cache_key: Key to store in cache
            ttl: Time to live in seconds
            priority: Priority (1=high, 2=medium, 3=low)
            enabled: Whether task is enabled
        """
        self.name = name
        self.fetch_func = fetch_func
        self.cache_key = cache_key
        self.ttl = ttl
        self.priority = priority
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.last_duration_ms: float = 0
        self.success_count: int = 0
        self.error_count: int = 0
        self.last_error: Optional[str] = None
    
    def execute(self) -> bool:
        """Execute the warming task"""
        if not self.enabled:
            return False
        
        start = time.perf_counter()
        try:
            from .cache_manager import get_cache_manager
            cache = get_cache_manager()
            
            if not cache.is_available():
                logger.warning("Cache not available for warming task: %s", self.name)
                return False
            
            # Fetch data
            data = self.fetch_func()
            
            if data is not None:
                # Store in cache
                cache.set(self.cache_key, data, ttl=self.ttl)
                
                self.last_run = datetime.utcnow()
                self.last_duration_ms = (time.perf_counter() - start) * 1000
                self.success_count += 1
                
                logger.debug(
                    "Warmed cache: %s (%.0fms)",
                    self.name, self.last_duration_ms
                )
                return True
            
            return False
            
        except (TypeError, ValueError, RuntimeError) as e:
            self.error_count += 1
            self.last_error = str(e)
            self.last_duration_ms = (time.perf_counter() - start) * 1000
            logger.error("Cache warming failed for %s: %s", self.name, e)
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "cache_key": self.cache_key,
            "ttl": self.ttl,
            "priority": self.priority,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_duration_ms": round(self.last_duration_ms, 2),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "last_error": self.last_error
        }


class CacheWarmer:
    """
    Service to warm up cache on startup and periodically
    
    Features:
    - Priority-based task execution
    - Parallel warming for performance
    - Background refresh scheduling
    - Statistics tracking
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        max_workers: int = 5,
        enable_background_refresh: bool = True,
        refresh_interval_seconds: int = 300
    ):
        """
        Initialize cache warmer
        
        Args:
            max_workers: Max parallel workers for warming
            enable_background_refresh: Enable background refresh thread
            refresh_interval_seconds: Interval between background refreshes
        """
        if self._initialized:  # pylint: disable=access-member-before-definition
            return
        
        self.max_workers = max_workers
        self.enable_background_refresh = enable_background_refresh
        self.refresh_interval = refresh_interval_seconds
        
        self._tasks: Dict[str, CacheWarmerTask] = {}
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._started = False
        
        self._initialized = True
        logger.info("Cache warmer initialized")
    
    def register_task(self, task: CacheWarmerTask):
        """Register a warming task"""
        self._tasks[task.name] = task
        logger.debug("Registered warming task: %s", task.name)
    
    def register(
        self,
        name: str,
        fetch_func: Callable[[], Any],
        cache_key: str,
        ttl: int = 300,
        priority: int = 1,
        enabled: bool = True
    ):
        """
        Convenience method to register a task
        
        Args:
            name: Task name
            fetch_func: Data fetch function
            cache_key: Cache key
            ttl: TTL in seconds
            priority: Priority (1=high)
            enabled: Whether enabled
        """
        task = CacheWarmerTask(
            name=name,
            fetch_func=fetch_func,
            cache_key=cache_key,
            ttl=ttl,
            priority=priority,
            enabled=enabled
        )
        self.register_task(task)
    
    def unregister(self, name: str):
        """Unregister a task"""
        self._tasks.pop(name, None)
    
    def has_task(self, name: str) -> bool:
        """Check if a task is registered"""
        return name in self._tasks
    
    def warm_all(self, parallel: bool = True) -> Dict[str, bool]:
        """
        Execute all warming tasks
        
        Args:
            parallel: Execute in parallel
            
        Returns:
            Dict mapping task name to success status
        """
        results = {}
        
        # Sort tasks by priority
        sorted_tasks = sorted(
            [t for t in self._tasks.values() if t.enabled],
            key=lambda t: t.priority
        )
        
        if not sorted_tasks:
            logger.info("No warming tasks to execute")
            return results
        
        start = time.perf_counter()
        logger.info("Starting cache warming (%d tasks)", len(sorted_tasks))
        
        if parallel and len(sorted_tasks) > 1:
            # Execute in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(task.execute): task.name
                    for task in sorted_tasks
                }
                
                for future in as_completed(futures):
                    task_name = futures[future]
                    try:
                        results[task_name] = future.result()
                    except (TypeError, ValueError, RuntimeError) as e:
                        logger.error("Task %s failed: %s", task_name, e)
                        results[task_name] = False
        else:
            # Execute sequentially
            for task in sorted_tasks:
                results[task.name] = task.execute()
        
        duration = (time.perf_counter() - start) * 1000
        success_count = sum(1 for v in results.values() if v)
        
        logger.info(
            "Cache warming complete: %d/%d succeeded (%.0fms)",
            success_count, len(results), duration
        )
        
        return results
    
    def warm_by_priority(self, priority: int) -> Dict[str, bool]:
        """Warm only tasks with specific priority"""
        results = {}
        
        for task in self._tasks.values():
            if task.enabled and task.priority == priority:
                results[task.name] = task.execute()
        
        return results
    
    def warm_single(self, name: str) -> bool:
        """Warm a single task by name"""
        task = self._tasks.get(name)
        if task:
            return task.execute()
        return False
    
    def start_background_refresh(self):
        """Start background refresh thread"""
        if not self.enable_background_refresh:
            return
        
        if self._refresh_thread and self._refresh_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._refresh_thread = threading.Thread(
            target=self._background_refresh_loop,
            daemon=True,
            name="CacheWarmerRefresh"
        )
        self._refresh_thread.start()
        logger.info("Started background cache refresh thread")
    
    def stop_background_refresh(self):
        """Stop background refresh thread"""
        self._stop_event.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=5)
            self._refresh_thread = None
        logger.info("Stopped background cache refresh thread")
    
    def _background_refresh_loop(self):
        """Background refresh loop"""
        while not self._stop_event.is_set():
            # Wait for interval
            self._stop_event.wait(self.refresh_interval)
            
            if self._stop_event.is_set():
                break
            
            # Refresh high priority tasks
            try:
                self.warm_by_priority(1)
            except (TypeError, ValueError, RuntimeError) as e:
                logger.error("Background refresh failed: %s", e)
    
    def startup(self):
        """
        Full startup procedure
        - Warm all caches
        - Start background refresh
        """
        if self._started:
            return
        
        logger.info("Cache warmer startup...")
        
        # Warm all caches
        self.warm_all()
        
        # Start background refresh
        self.start_background_refresh()
        
        self._started = True
        logger.info("Cache warmer startup complete")
    
    def shutdown(self):
        """Shutdown procedure"""
        self.stop_background_refresh()
        self._started = False
        logger.info("Cache warmer shutdown complete")
    
    def get_task_stats(self) -> Dict[str, Dict]:
        """Get statistics for all tasks"""
        return {
            name: task.to_dict()
            for name, task in self._tasks.items()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        total_tasks = len(self._tasks)
        enabled_tasks = sum(1 for t in self._tasks.values() if t.enabled)
        total_success = sum(t.success_count for t in self._tasks.values())
        total_errors = sum(t.error_count for t in self._tasks.values())
        
        return {
            "total_tasks": total_tasks,
            "enabled_tasks": enabled_tasks,
            "total_success": total_success,
            "total_errors": total_errors,
            "background_refresh_enabled": self.enable_background_refresh,
            "refresh_interval_seconds": self.refresh_interval,
            "is_running": self._started
        }


# =========================================================================
# Pre-built Warming Tasks for expense_engine
# =========================================================================

def create_user_groups_warmer(user_id: str, ttl: int = 60) -> CacheWarmerTask:
    """
    Create warming task for user's groups
    
    Args:
        user_id: User ID
        ttl: Cache TTL
        
    Returns:
        CacheWarmerTask
    """
    def fetch():
        try:
            from ..repositories.group_repository import GroupRepository
            repo = GroupRepository()
            return repo.get_user_groups(user_id)
        except (TypeError, ValueError, RuntimeError) as e:
            logger.error("Failed to fetch user groups for %s: %s", user_id, e)
            return None
    
    return CacheWarmerTask(
        name=f"user_groups:{user_id}",
        fetch_func=fetch,
        cache_key=f"expense:user_groups:{user_id}",
        ttl=ttl,
        priority=1
    )


def create_group_balances_warmer(group_id: str, ttl: int = 30) -> CacheWarmerTask:
    """
    Create warming task for group balances
    
    Args:
        group_id: Group ID
        ttl: Cache TTL
        
    Returns:
        CacheWarmerTask
    """
    def fetch():
        try:
            from ..repositories.balance_repository import BalanceRepository
            repo = BalanceRepository()
            return repo.get_group_balances(group_id)
        except (TypeError, ValueError, RuntimeError) as e:
            logger.error("Failed to fetch balances for %s: %s", group_id, e)
            return None
    
    return CacheWarmerTask(
        name=f"group_balances:{group_id}",
        fetch_func=fetch,
        cache_key=f"expense:balance:{group_id}",
        ttl=ttl,
        priority=1
    )


def create_group_full_warmer(group_id: str, ttl: int = 30) -> CacheWarmerTask:
    """
    Create warming task for full group data
    
    Args:
        group_id: Group ID
        ttl: Cache TTL
        
    Returns:
        CacheWarmerTask
    """
    def fetch():
        try:
            from ..services.group_service import GroupService
            service = GroupService()
            # Use get_group method instead of get_group_full
            return service.get_group(group_id)
        except (TypeError, ValueError, RuntimeError) as e:
            logger.error("Failed to fetch full group %s: %s", group_id, e)
            return None
    
    return CacheWarmerTask(
        name=f"group_full:{group_id}",
        fetch_func=fetch,
        cache_key=f"expense:group_full:{group_id}",
        ttl=ttl,
        priority=2
    )


def register_active_groups_warming(
    warmer: CacheWarmer,
    active_user_ids: List[str],
    ttl: int = 60
):
    """
    Register warming tasks for active users' groups
    
    Args:
        warmer: CacheWarmer instance
        active_user_ids: List of active user IDs
        ttl: Cache TTL
    """
    for user_id in active_user_ids:
        task = create_user_groups_warmer(user_id, ttl)
        warmer.register_task(task)
    
    logger.info("Registered %d user groups warming tasks", len(active_user_ids))


def register_recent_groups_warming(
    warmer: CacheWarmer,
    group_ids: List[str],
    ttl: int = 30
):
    """
    Register warming tasks for recently accessed groups
    
    Args:
        warmer: CacheWarmer instance
        group_ids: List of group IDs
        ttl: Cache TTL
    """
    for group_id in group_ids:
        # Register balances warmer (high priority)
        balances_task = create_group_balances_warmer(group_id, ttl)
        warmer.register_task(balances_task)
        
        # Register full group warmer (medium priority)
        full_task = create_group_full_warmer(group_id, ttl)
        warmer.register_task(full_task)
    
    logger.info("Registered warming tasks for %d groups", len(group_ids))


# =========================================================================
# Global Cache Warmer Instance
# =========================================================================

_cache_warmer: Optional[CacheWarmer] = None


def get_cache_warmer() -> CacheWarmer:
    """Get the global cache warmer instance"""
    global _cache_warmer  # pylint: disable=global-statement
    if _cache_warmer is None:
        _cache_warmer = CacheWarmer()
    return _cache_warmer


def initialize_cache_warming():
    """
    Initialize cache warming on application startup
    
    This should be called during Flask app initialization
    """
    warmer = get_cache_warmer()
    
    # Register common warming tasks
    # These are examples - actual implementation depends on your data model
    
    # Example: System-wide statistics
    warmer.register(
        name="system_stats",
        fetch_func=lambda: {"status": "ok", "timestamp": datetime.utcnow().isoformat()},
        cache_key="expense:analytics:system_stats",
        ttl=300,
        priority=3
    )
    
    # Start the warmer
    warmer.startup()
    
    return warmer


def warm_cache_for_user(user_id: str):
    """
    Warm cache for a specific user (call on login)
    
    Args:
        user_id: User ID
    """
    # Register and execute user groups warming
    task = create_user_groups_warmer(user_id)
    task.execute()


def warm_cache_for_group(group_id: str):
    """
    Warm cache for a specific group (call when group is accessed)
    
    Args:
        group_id: Group ID
    """
    # Execute both balances and full group warming
    balances_task = create_group_balances_warmer(group_id)
    balances_task.execute()


# =========================================================================
# Flask Integration
# =========================================================================

def init_flask_cache_warming(app):
    """
    Initialize cache warming for Flask application
    
    Args:
        app: Flask application instance
    """
    warmer = initialize_cache_warming()
    
    # Store warmer in app context
    app.cache_warmer = warmer
    
    # Register teardown
    @app.teardown_appcontext
    def shutdown_warmer(exception=None):  # pylint: disable=unused-argument
        pass  # Don't shutdown on every request
    
    # Add CLI commands
    @app.cli.command("warm-cache")
    def warm_cache_cli():
        """Warm all caches"""
        results = warmer.warm_all()
        print(f"Warmed {sum(results.values())}/{len(results)} caches")
    
    @app.cli.command("cache-warmer-stats")
    def warmer_stats_cli():
        """Show cache warmer statistics"""
        import json
        print(json.dumps(warmer.get_summary(), indent=2))
    
    logger.info("Flask cache warming initialized")


# =========================================================================
# Decorator for Automatic Cache Warming
# =========================================================================

def warm_on_access(
    cache_key_func: Callable[..., str],
    ttl: int = 60,
    priority: int = 2
):
    """
    Decorator to automatically register cache warming on first access
    
    Args:
        cache_key_func: Function to generate cache key from args
        ttl: Cache TTL
        priority: Task priority
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            warmer = get_cache_warmer()
            
            # Generate cache key and task name
            cache_key = cache_key_func(*args, **kwargs)
            task_name = f"auto:{func.__name__}:{cache_key}"
            
            # Register warming task if not already registered
            if not warmer.has_task(task_name):
                warmer.register(
                    name=task_name,
                    fetch_func=lambda: func(*args, **kwargs),
                    cache_key=cache_key,
                    ttl=ttl,
                    priority=priority
                )
            
            # Execute function
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator
