"""
Cached Repository Mixin
Adds transparent caching to repository methods

Phase 5: Performance Optimization
"""

import logging
from typing import Optional, Dict, Any, List, Callable, TypeVar
from functools import wraps

from .base import BaseRepository
from ..utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CachedRepositoryMixin:
    """
    Mixin to add caching capabilities to any repository
    
    Usage:
        class ExpenseRepository(CachedRepositoryMixin, BaseRepository):
            cache_prefix = "expense:expense"
            cache_ttl = 60
    """
    
    # Override these in subclass
    cache_prefix: str = "expense"
    cache_ttl: int = 60
    cache_enabled: bool = True
    
    @property
    def cache(self):
        """Get cache manager"""
        return get_cache_manager()
    
    def _cache_key(self, *parts: str) -> str:
        """Generate cache key from parts"""
        return f"{self.cache_prefix}:{':'.join(str(p) for p in parts if p)}"
    
    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.cache_enabled:
            return None
        return self.cache.get(cache_key)
    
    def _set_cached(self, cache_key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.cache_enabled:
            return False
        return self.cache.set(cache_key, value, ttl=ttl or self.cache_ttl)
    
    def _invalidate(self, *cache_keys: str) -> int:
        """Invalidate cache keys"""
        if not self.cache_enabled:
            return 0
        return self.cache.delete(*cache_keys)
    
    def get_cached_by_id(self, doc_id: str) -> Optional[Dict]:
        """
        Get document by ID with caching
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document data or None
        """
        cache_key = self._cache_key("id", doc_id)
        
        # Try cache first
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug("Cache HIT: %s", cache_key)
            return cached
        
        # Fetch from Firestore
        logger.debug("Cache MISS: %s", cache_key)
        data = super().get_by_id(doc_id)
        
        # Cache result
        if data:
            self._set_cached(cache_key, data)
        
        return data
    
    def cached_query(
        self,
        cache_key: str,
        query_func: Callable[[], List[Dict]],
        ttl: Optional[int] = None
    ) -> List[Dict]:
        """
        Execute query with caching
        
        Args:
            cache_key: Cache key for results
            query_func: Function to execute query
            ttl: Optional TTL override
            
        Returns:
            List of documents
        """
        # Try cache first
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug("Cache HIT: %s", cache_key)
            return cached
        
        # Execute query
        logger.debug("Cache MISS: %s", cache_key)
        results = query_func()
        
        # Cache results
        if results:
            self._set_cached(cache_key, results, ttl)
        
        return results
    
    def invalidate_document(self, doc_id: str):
        """Invalidate cache for a document"""
        cache_key = self._cache_key("id", doc_id)
        self._invalidate(cache_key)
        logger.debug("Invalidated: %s", cache_key)
    
    def invalidate_collection(self):
        """Invalidate all cached data for this collection"""
        pattern = f"{self.cache_prefix}:*"
        count = self.cache.delete_pattern(pattern)
        logger.debug("Invalidated %d keys matching %s", count, pattern)
        return count


def cached_method(cache_key_func: Callable[..., str], ttl: Optional[int] = None):
    """
    Decorator for caching repository method results
    
    Args:
        cache_key_func: Function to generate cache key from method args
        ttl: Cache TTL (uses repository default if not specified)
        
    Returns:
        Decorated method
        
    Example:
        @cached_method(
            cache_key_func=lambda self, group_id: f"group_expenses:{group_id}",
            ttl=30
        )
        def get_group_expenses(self, group_id: str) -> List[Dict]:
            ...
    """
    def decorator(method: Callable[..., T]) -> Callable[..., T]:
        @wraps(method)
        def wrapper(self, *args, **kwargs) -> T:
            # Check if caching is enabled
            if not getattr(self, 'cache_enabled', True):
                return method(self, *args, **kwargs)
            
            # Generate cache key
            cache_key = cache_key_func(self, *args, **kwargs)
            
            # Get cache manager
            cache = get_cache_manager()
            
            # Try cache first
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT: %s", cache_key)
                return cached
            
            # Execute method
            logger.debug("Cache MISS: %s", cache_key)
            result = method(self, *args, **kwargs)
            
            # Cache result
            if result is not None:
                effective_ttl = ttl or getattr(self, 'cache_ttl', 60)
                cache.set(cache_key, result, ttl=effective_ttl)
            
            return result
        
        # Attach invalidation helper
        def invalidate(self, *args, **kwargs):
            cache_key = cache_key_func(self, *args, **kwargs)
            get_cache_manager().delete(cache_key)
        
        wrapper.invalidate = invalidate
        return wrapper
    
    return decorator


def invalidate_after(
    invalidate_keys: Optional[List[str]] = None,
    invalidate_func: Optional[Callable[..., List[str]]] = None
):
    """
    Decorator to invalidate cache after method execution
    
    Args:
        invalidate_keys: Static list of keys to invalidate
        invalidate_func: Function to compute keys from method args
        
    Returns:
        Decorated method
        
    Example:
        @invalidate_after(
            invalidate_func=lambda self, group_id, data: [
                f"expense:group:{group_id}",
                f"expense:balance:{group_id}"
            ]
        )
        def create_expense(self, group_id: str, data: Dict) -> Dict:
            ...
    """
    def decorator(method: Callable[..., T]) -> Callable[..., T]:
        @wraps(method)
        def wrapper(self, *args, **kwargs) -> T:
            # Execute method first
            result = method(self, *args, **kwargs)
            
            # Determine keys to invalidate
            keys_to_invalidate = []
            
            if invalidate_keys:
                keys_to_invalidate.extend(invalidate_keys)
            
            if invalidate_func:
                computed_keys = invalidate_func(self, *args, result=result, **kwargs)
                if computed_keys:
                    keys_to_invalidate.extend(computed_keys)
            
            # Invalidate keys
            if keys_to_invalidate:
                cache = get_cache_manager()
                cache.delete(*keys_to_invalidate)
                logger.debug(
                    "Invalidated %d keys after %s",
                    len(keys_to_invalidate), method.__name__
                )
            
            return result
        
        return wrapper
    
    return decorator


# =========================================================================
# Pre-built Cache Key Functions for Common Patterns
# =========================================================================

def group_cache_key(prefix: str):
    """Generate cache key function for group-based queries"""
    def key_func(_self, group_id: str, *_args, **_kwargs) -> str:
        return f"{prefix}:{group_id}"
    return key_func


def user_cache_key(prefix: str):
    """Generate cache key function for user-based queries"""
    def key_func(_self, user_id: str, *_args, **_kwargs) -> str:
        return f"{prefix}:{user_id}"
    return key_func


def paginated_cache_key(prefix: str):
    """Generate cache key function for paginated queries"""
    def key_func(_self, entity_id: str, limit: int = 20, offset: int = 0, **_kwargs) -> str:
        return f"{prefix}:{entity_id}:l{limit}:o{offset}"
    return key_func


# =========================================================================
# Cache-aware Base Repository
# =========================================================================

class CacheAwareRepository(CachedRepositoryMixin, BaseRepository):
    """
    Base repository with built-in caching support
    
    Subclass this instead of BaseRepository to get automatic caching.
    
    Example:
        class ExpenseRepository(CacheAwareRepository):
            cache_prefix = "expense:expense"
            cache_ttl = 60
            
            def get_collection_name(self) -> str:
                return "expense_expenses"
    """
    
    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        """Override to use caching"""
        return self.get_cached_by_id(doc_id)
    
    def create(self, doc_id: str, data: Dict) -> str:
        """Override to invalidate cache"""
        result = super().create(doc_id, data)
        # No need to invalidate on create
        return result
    
    def update(self, doc_id: str, data: Dict) -> None:
        """Override to invalidate cache"""
        super().update(doc_id, data)
        self.invalidate_document(doc_id)
    
    def delete(self, doc_id: str) -> None:
        """Override to invalidate cache"""
        super().delete(doc_id)
        self.invalidate_document(doc_id)
    
    def soft_delete(self, doc_id: str, deleted_at_field: str = 'deleted_at',
                    is_deleted_field: str = 'is_deleted') -> None:
        """Override to invalidate cache"""
        super().soft_delete(doc_id, deleted_at_field, is_deleted_field)
        self.invalidate_document(doc_id)
    
    def restore(self, doc_id: str, deleted_at_field: str = 'deleted_at',
                is_deleted_field: str = 'is_deleted') -> None:
        """Override to invalidate cache"""
        super().restore(doc_id, deleted_at_field, is_deleted_field)
        self.invalidate_document(doc_id)
