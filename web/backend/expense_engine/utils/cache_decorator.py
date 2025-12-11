"""
Cache Decorator - Automatic Method Caching
Provides @cached decorator for repository and service methods

Phase 5: Performance Optimization
"""

import hashlib
import logging
from functools import wraps
from typing import Optional, Callable, Any, TypeVar, List

logger = logging.getLogger(__name__)

T = TypeVar('T')


def _generate_cache_key(
    prefix: str,
    func_name: str,
    args: tuple,
    kwargs: dict,
    key_params: Optional[List[str]] = None
) -> str:
    """
    Generate a unique cache key based on function call
    
    Args:
        prefix: Key prefix (e.g., "expense:group:")
        func_name: Function name
        args: Positional arguments
        kwargs: Keyword arguments
        key_params: Specific parameters to include in key
        
    Returns:
        Unique cache key string
    """
    # Start with prefix and function name
    key_parts = [prefix, func_name]
    
    # If specific key params requested, use only those
    if key_params:
        for param in key_params:
            if param in kwargs:
                key_parts.append(str(kwargs[param]))
    else:
        # Include all args (skip self)
        for arg in args[1:]:  # Skip self
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            elif isinstance(arg, (list, tuple)):
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Include kwargs (sorted for consistency)
        for key in sorted(kwargs.keys()):
            value = kwargs[key]
            if isinstance(value, (str, int, float, bool)):
                key_parts.append(f"{key}:{value}")
            elif value is not None:
                key_parts.append(f"{key}:{hashlib.md5(str(value).encode()).hexdigest()[:8]}")
    
    return ":".join(str(p) for p in key_parts if p)


def cached(
    prefix: str,
    ttl: int = 60,
    key_params: Optional[List[str]] = None,
    condition: Optional[Callable[..., bool]] = None,
    invalidate_on_error: bool = False
):
    """
    Decorator to cache function results in Redis
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_params: Specific parameters to include in cache key
        condition: Optional function to determine if result should be cached
        invalidate_on_error: If True, invalidate cache on error
        
    Returns:
        Decorated function
        
    Example:
        @cached(prefix="expense:group", ttl=60, key_params=["group_id"])
        def get_group(self, group_id: str) -> Dict:
            return self.repo.get_by_id(group_id)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Import cache manager
            try:
                from .cache_manager import get_cache_manager
                cache = get_cache_manager()
            except ImportError:
                logger.warning("Cache manager not available, executing without cache")
                return func(*args, **kwargs)
            
            # Generate cache key
            cache_key = _generate_cache_key(
                prefix=prefix,
                func_name=func.__name__,
                args=args,
                kwargs=kwargs,
                key_params=key_params
            )
            
            # Try to get from cache
            if cache.is_available():
                cached_value = cache.get(cache_key)
                if cached_value is not None:
                    logger.debug("Cache HIT: %s", cache_key)
                    return cached_value
                logger.debug("Cache MISS: %s", cache_key)
            
            # Execute function
            try:
                result = func(*args, **kwargs)
                
                # Check condition before caching
                if condition and not condition(result):
                    return result
                
                # Cache result
                if result is not None and cache.is_available():
                    cache.set(cache_key, result, ttl=ttl)
                    logger.debug("Cached result: %s (TTL: %ds)", cache_key, ttl)
                
                return result
                
            except Exception:
                if invalidate_on_error and cache.is_available():
                    cache.delete(cache_key)
                raise
        
        # Attach cache control methods
        wrapper.cache_key_prefix = prefix
        wrapper.cache_ttl = ttl
        
        def invalidate_cache(*args, **kwargs):
            """Invalidate cache for specific call"""
            try:
                from .cache_manager import get_cache_manager
                cache = get_cache_manager()
                cache_key = _generate_cache_key(
                    prefix=prefix,
                    func_name=func.__name__,
                    args=args,
                    kwargs=kwargs,
                    key_params=key_params
                )
                return cache.delete(cache_key)
            except ImportError:
                return 0
        
        wrapper.invalidate = invalidate_cache
        return wrapper
    
    return decorator


def cached_property(
    prefix: str,
    ttl: int = 300,
    key_func: Optional[Callable[[Any], str]] = None
):
    """
    Decorator for caching property results
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_func: Function to generate key from self
        
    Returns:
        Decorated property
        
    Example:
        @cached_property(prefix="expense:user", ttl=300, key_func=lambda self: self.user_id)
        def user_profile(self) -> Dict:
            return self._load_profile()
    """
    def decorator(func: Callable[[Any], T]) -> property:
        @wraps(func)
        def getter(self) -> T:
            try:
                from .cache_manager import get_cache_manager
                cache = get_cache_manager()
            except ImportError:
                return func(self)
            
            # Generate key
            if key_func:
                cache_key = f"{prefix}:{key_func(self)}"
            else:
                cache_key = f"{prefix}:{id(self)}"
            
            # Check cache
            if cache.is_available():
                cached_value = cache.get(cache_key)
                if cached_value is not None:
                    return cached_value
            
            # Get value
            result = func(self)
            
            # Cache it
            if result is not None and cache.is_available():
                cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return property(getter)
    
    return decorator


def cache_aside(
    get_from_cache: Callable[[str], Optional[T]],
    set_to_cache: Callable[[str, T], bool]
):
    """
    Cache-aside pattern decorator
    
    Args:
        get_from_cache: Function to retrieve from cache
        set_to_cache: Function to store in cache
        ttl: Time to live
        
    Returns:
        Decorated function
        
    Example:
        @cache_aside(
            get_from_cache=lambda key: cache.get(key),
            set_to_cache=lambda key, val: cache.set(key, val, ttl=60)
        )
        def get_user(self, user_id: str) -> Dict:
            cache_key = f"user:{user_id}"
            return self.repo.get_by_id(user_id), cache_key
    """
    def decorator(func: Callable[..., tuple]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Function returns (result, cache_key) tuple
            result, cache_key = func(*args, **kwargs)
            
            # Try cache first
            cached_value = get_from_cache(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Get fresh value
            if result is not None:
                set_to_cache(cache_key, result)
            
            return result
        
        return wrapper
    
    return decorator


class CachedRepository:
    """
    Mixin class to add caching capabilities to repositories
    
    Example:
        class ExpenseRepository(CachedRepository, BaseRepository):
            cache_prefix = "expense:expense"
            cache_ttl = 60
    """
    
    cache_prefix: str = "expense"
    cache_ttl: int = 60
    _cache_manager = None
    
    @property
    def cache(self):
        """Get cache manager"""
        if self._cache_manager is None:
            try:
                from .cache_manager import get_cache_manager
                self._cache_manager = get_cache_manager()
            except ImportError:
                return None
        return self._cache_manager
    
    def _cache_key(self, *parts: str) -> str:
        """Generate cache key"""
        return f"{self.cache_prefix}:{':'.join(str(p) for p in parts)}"
    
    def get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.cache and self.cache.is_available():
            return self.cache.get(key)
        return None
    
    def set_to_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if self.cache and self.cache.is_available():
            return self.cache.set(key, value, ttl=ttl or self.cache_ttl)
        return False
    
    def invalidate_cache(self, *keys: str) -> int:
        """Invalidate cache keys"""
        if self.cache and self.cache.is_available():
            return self.cache.delete(*keys)
        return 0
    
    def get_cached(
        self,
        cache_key: str,
        fetch_func: Callable[[], T],
        ttl: Optional[int] = None
    ) -> Optional[T]:
        """
        Get value from cache or fetch and cache it
        
        Args:
            cache_key: Cache key
            fetch_func: Function to fetch value if not cached
            ttl: Optional TTL override
            
        Returns:
            Cached or fetched value
        """
        # Try cache first
        cached_value = self.get_from_cache(cache_key)
        if cached_value is not None:
            return cached_value
        
        # Fetch fresh value
        value = fetch_func()
        
        # Cache it
        if value is not None:
            self.set_to_cache(cache_key, value, ttl)
        
        return value


def invalidate_on_write(
    invalidate_keys: Optional[List[str]] = None,
    invalidate_patterns: Optional[List[str]] = None,
    invalidate_related: Optional[Callable[..., List[str]]] = None
):
    """
    Decorator to invalidate cache after write operations
    
    Args:
        invalidate_keys: Specific keys to invalidate
        invalidate_patterns: Key patterns to invalidate
        invalidate_related: Function to determine related keys from args/result
        
    Returns:
        Decorated function
        
    Example:
        @invalidate_on_write(
            invalidate_patterns=["expense:group:{group_id}:*"],
            invalidate_related=lambda result: [f"expense:user_groups:{uid}" for uid in result.get('member_ids', [])]
        )
        def create_expense(self, group_id: str, data: Dict) -> Dict:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Execute function first
            result = func(*args, **kwargs)
            
            # Invalidate cache
            try:
                from .cache_manager import get_cache_manager
                cache = get_cache_manager()
                
                if not cache.is_available():
                    return result
                
                keys_to_delete = []
                
                # Add specific keys
                if invalidate_keys:
                    # Interpolate keys with kwargs
                    for key in invalidate_keys:
                        try:
                            formatted_key = key.format(**kwargs)
                            keys_to_delete.append(formatted_key)
                        except KeyError:
                            keys_to_delete.append(key)
                
                # Add pattern-matched keys
                if invalidate_patterns:
                    for pattern in invalidate_patterns:
                        try:
                            formatted_pattern = pattern.format(**kwargs)
                            # Use delete_pattern for pattern-based invalidation
                            cache.delete_pattern(formatted_pattern)
                        except (KeyError, AttributeError):
                            pass
                
                # Add related keys from result
                if invalidate_related and result:
                    related_keys = invalidate_related(result)
                    if related_keys:
                        keys_to_delete.extend(related_keys)
                
                # Delete all collected keys
                if keys_to_delete:
                    cache.delete(*keys_to_delete)
                    logger.debug("Invalidated %d cache keys after %s", len(keys_to_delete), func.__name__)
                
            except (ImportError, AttributeError) as e:
                logger.warning("Cache invalidation failed: %s", str(e))
            
            return result
        
        return wrapper
    
    return decorator


# =========================================================================
# Utility Functions
# =========================================================================

def warm_cache(
    cache_func: Callable[[], Any],
    cache_key: str,
    ttl: int = 300,
    condition: Optional[Callable[[], bool]] = None
) -> bool:
    """
    Warm up cache with pre-fetched data
    
    Args:
        cache_func: Function to fetch data
        cache_key: Cache key to store data
        ttl: Time to live
        condition: Optional condition to check before warming
        
    Returns:
        True if cache was warmed successfully
    """
    try:
        from .cache_manager import get_cache_manager
        cache = get_cache_manager()
        
        if not cache.is_available():
            return False
        
        # Check condition
        if condition and not condition():
            return False
        
        # Fetch and cache data
        data = cache_func()
        if data is not None:
            return cache.set(cache_key, data, ttl=ttl)
        
        return False
    except (ImportError, AttributeError) as e:
        logger.error("Cache warming failed for %s: %s", cache_key, str(e))
        return False


def batch_warm_cache(items: List[dict]) -> dict:
    """
    Warm multiple cache entries at once
    
    Args:
        items: List of dicts with 'key', 'data', and optional 'ttl'
        
    Returns:
        Dict with success count and failures
    """
    try:
        from .cache_manager import get_cache_manager
        cache = get_cache_manager()
        
        if not cache.is_available():
            return {"success": 0, "failed": len(items)}
        
        success = 0
        failed = 0
        
        for item in items:
            key = item.get('key')
            data = item.get('data')
            ttl = item.get('ttl', 300)
            
            if key and data is not None:
                if cache.set(key, data, ttl=ttl):
                    success += 1
                else:
                    failed += 1
            else:
                failed += 1
        
        return {"success": success, "failed": failed}
    except (ImportError, AttributeError) as e:
        logger.error("Batch cache warming failed: %s", str(e))
        return {"success": 0, "failed": len(items), "error": str(e)}
