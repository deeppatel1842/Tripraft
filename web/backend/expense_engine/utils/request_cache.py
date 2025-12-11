"""
Request-scoped document cache to avoid duplicate Firestore reads within a single HTTP request.

Phase 17.1: Kill Duplicate Reads

Problem: Same document (e.g., expense_groups/XXX) read 2-4 times in one API call
Solution: Cache documents at the request level using Flask's 'g' object

Usage:
    from expense_engine.utils.request_cache import get_request_cache, cache_document_read

    # Manual usage
    cache = get_request_cache()
    cached_doc = cache.get('expense_groups', 'group123')
    if cached_doc is None:
        doc = firestore_read(...)
        cache.set('expense_groups', 'group123', doc)

    # Decorator usage (on repository methods)
    @cache_document_read
    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        ...
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar
from flask import g, has_request_context

logger = logging.getLogger(__name__)

# Type variable for generic function signatures
F = TypeVar('F', bound=Callable[..., Any])


class RequestDocumentCache:
    """
    Cache for documents within a single HTTP request.
    
    This cache lives only for the duration of one request and is automatically
    cleared when the request ends. It prevents the same Firestore document
    from being read multiple times within a single API call.
    
    Attributes:
        _cache: Dict storing cached documents keyed by "collection/doc_id"
        _stats: Dict tracking cache hits and misses for monitoring
    """
    
    def __init__(self):
        """Initialize empty cache and stats."""
        self._cache: Dict[str, Any] = {}
        self._stats: Dict[str, int] = {
            'hits': 0,
            'misses': 0,
            'sets': 0
        }
    
    def _make_key(self, collection: str, doc_id: str) -> str:
        """
        Create a cache key from collection and document ID.
        
        Args:
            collection: Firestore collection name
            doc_id: Document ID
            
        Returns:
            Cache key in format "collection/doc_id"
        """
        return f"{collection}/{doc_id}"
    
    def get(self, collection: str, doc_id: str) -> Optional[Dict]:
        """
        Get a document from the request cache.
        
        Args:
            collection: Firestore collection name
            doc_id: Document ID
            
        Returns:
            Cached document dict or None if not cached
        """
        key = self._make_key(collection, doc_id)
        if key in self._cache:
            self._stats['hits'] += 1
            logger.debug(f"[REQUEST_CACHE][+] HIT: {key}")
            return self._cache[key]
        
        self._stats['misses'] += 1
        logger.debug(f"[REQUEST_CACHE][-] MISS: {key}")
        return None
    
    def set(self, collection: str, doc_id: str, data: Dict) -> None:
        """
        Store a document in the request cache.
        
        Args:
            collection: Firestore collection name
            doc_id: Document ID
            data: Document data to cache
        """
        if data is None:
            return
            
        key = self._make_key(collection, doc_id)
        self._cache[key] = data
        self._stats['sets'] += 1
        logger.debug(f"[REQUEST_CACHE][S] SET: {key}")
    
    def delete(self, collection: str, doc_id: str) -> bool:
        """
        Remove a document from the request cache.
        
        Useful when a document is updated/deleted and we want to ensure
        subsequent reads get fresh data.
        
        Args:
            collection: Firestore collection name
            doc_id: Document ID
            
        Returns:
            True if document was in cache and removed, False otherwise
        """
        key = self._make_key(collection, doc_id)
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"[REQUEST_CACHE][X] DELETE: {key}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cached documents."""
        count = len(self._cache)
        self._cache.clear()
        logger.debug(f"[REQUEST_CACHE] Cleared {count} cached documents")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics for this request.
        
        Returns:
            Dict with 'hits', 'misses', and 'sets' counts
        """
        return self._stats.copy()
    
    def get_hit_rate(self) -> float:
        """
        Calculate cache hit rate for this request.
        
        Returns:
            Hit rate as a percentage (0-100), or 0 if no lookups
        """
        total = self._stats['hits'] + self._stats['misses']
        if total == 0:
            return 0.0
        return (self._stats['hits'] / total) * 100
    
    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        return key in self._cache
    
    def __len__(self) -> int:
        """Return number of cached documents."""
        return len(self._cache)


def get_request_cache() -> RequestDocumentCache:
    """
    Get or create the request-scoped document cache.
    
    Uses Flask's 'g' object to store the cache, ensuring it's automatically
    cleaned up at the end of each request.
    
    Returns:
        RequestDocumentCache instance for the current request
    """
    if not has_request_context():
        # Return a dummy cache if not in request context (e.g., in tests)
        return RequestDocumentCache()
    
    if not hasattr(g, '_request_doc_cache'):
        g._request_doc_cache = RequestDocumentCache()
    
    return g._request_doc_cache


def cache_document_read(func: F) -> F:
    """
    Decorator to cache document reads within a request.
    
    Designed for repository methods like get_by_id(). The decorator:
    1. Checks if the document is already cached for this request
    2. If cached, returns the cached value (avoiding Firestore read)
    3. If not cached, calls the original function and caches the result
    
    Requirements:
        - The decorated method must be on a class with _collection_name attribute
        - First argument (after self) must be the document ID
    
    Example:
        class ExpenseRepository(BaseRepository):
            @cache_document_read
            def get_by_id(self, doc_id: str) -> Optional[Dict]:
                # This will only hit Firestore once per request per doc_id
                return self._get_document(doc_id)
    """
    @wraps(func)
    def wrapper(self, doc_id: str, *args, **kwargs):
        # Get collection name from repository instance
        collection = getattr(self, '_collection_name', None)
        if collection is None:
            # Fallback: try to get from collection_name property
            collection = getattr(self, 'collection_name', 'unknown')
        
        # Check cache first
        cache = get_request_cache()
        cached_result = cache.get(collection, doc_id)
        
        if cached_result is not None:
            return cached_result
        
        # Call original function
        result = func(self, doc_id, *args, **kwargs)
        
        # Cache the result if not None
        if result is not None:
            cache.set(collection, doc_id, result)
        
        return result
    
    return wrapper  # type: ignore


def cache_query_result(collection: str, query_key: str):
    """
    Decorator to cache query results within a request.
    
    Unlike cache_document_read (which caches individual documents),
    this caches the results of queries that return multiple documents.
    
    Args:
        collection: Collection name for the query
        query_key: A unique identifier for this query type
        
    Example:
        @cache_query_result('expense_groups', 'user_groups')
        def get_user_groups(self, user_id: str) -> List[Dict]:
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function arguments
            cache_id = f"{query_key}:{':'.join(str(a) for a in args[1:])}"
            
            cache = get_request_cache()
            cached_result = cache.get(collection, cache_id)
            
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            
            if result is not None:
                cache.set(collection, cache_id, result)
            
            return result
        
        return wrapper  # type: ignore
    
    return decorator


def invalidate_cached_document(collection: str, doc_id: str) -> None:
    """
    Invalidate a cached document after it's been modified.
    
    Call this after updating or deleting a document to ensure
    subsequent reads within the same request get fresh data.
    
    Args:
        collection: Firestore collection name
        doc_id: Document ID to invalidate
    """
    cache = get_request_cache()
    cache.delete(collection, doc_id)


def update_cached_document(collection: str, doc_id: str, data: Dict) -> None:
    """
    Update a cached document with new data.
    
    Call this after writing a document to update the cache with the written
    value, avoiding the need to re-read from Firestore.
    
    Args:
        collection: Firestore collection name
        doc_id: Document ID
        data: New document data
    """
    cache = get_request_cache()
    cache.set(collection, doc_id, data)


def log_request_cache_stats() -> Dict[str, Any]:
    """
    Log and return cache statistics for the current request.
    
    Call this at the end of a request (e.g., in after_request hook)
    to monitor cache effectiveness.
    
    Returns:
        Dict with cache statistics
    """
    cache = get_request_cache()
    stats = cache.get_stats()
    hit_rate = cache.get_hit_rate()
    
    if stats['hits'] + stats['misses'] > 0:
        logger.info(
            f"[REQUEST_CACHE] Stats: {stats['hits']} hits, {stats['misses']} misses, "
            f"{stats['sets']} sets, {hit_rate:.1f}% hit rate"
        )
    
    return {
        **stats,
        'hit_rate': hit_rate,
        'cached_docs': len(cache)
    }
