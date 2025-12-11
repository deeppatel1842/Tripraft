"""
Query Optimizer - Firestore Query Optimization
Optimized queries with caching and batching support

Phase 5: Performance Optimization
"""

import logging
from typing import Optional, List, Dict, Any, Callable, TypeVar, Tuple
from datetime import datetime, timedelta
import threading
import hashlib

logger = logging.getLogger(__name__)

T = TypeVar('T')


class QueryResult:
    """Wrapper for query results with metadata"""
    
    def __init__(
        self,
        data: List[Dict],
        total_count: Optional[int] = None,
        has_more: bool = False,
        cursor: Optional[str] = None,
        cached: bool = False,
        query_time_ms: float = 0
    ):
        self.data = data
        self.total_count = total_count
        self.has_more = has_more
        self.cursor = cursor
        self.cached = cached
        self.query_time_ms = query_time_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "total_count": self.total_count,
            "has_more": self.has_more,
            "cursor": self.cursor,
            "cached": self.cached,
            "query_time_ms": round(self.query_time_ms, 2)
        }
    
    def __len__(self) -> int:
        return len(self.data)
    
    def __iter__(self):
        return iter(self.data)


class QueryBuilder:
    """
    Fluent query builder for Firestore
    
    Example:
        results = (
            QueryBuilder(collection_ref)
            .where("group_id", "==", "group123")
            .where("is_deleted", "==", False)
            .order_by("created_at", "DESCENDING")
            .limit(20)
            .execute()
        )
    """
    
    def __init__(self, collection_ref):
        """
        Initialize query builder
        
        Args:
            collection_ref: Firestore collection reference
        """
        self._collection = collection_ref
        self._query = collection_ref
        self._filters: List[Tuple] = []
        self._order_by: Optional[Tuple] = None
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._start_after = None
        self._select_fields: Optional[List[str]] = None
    
    def where(self, field: str, operator: str, value: Any) -> 'QueryBuilder':
        """Add filter condition"""
        self._filters.append((field, operator, value))
        self._query = self._query.where(field, operator, value)
        return self
    
    def order_by(self, field: str, direction: str = "ASCENDING") -> 'QueryBuilder':
        """Add ordering"""
        from google.cloud.firestore_v1 import Query
        dir_map = {
            "ASCENDING": Query.ASCENDING,
            "DESCENDING": Query.DESCENDING,
            "ASC": Query.ASCENDING,
            "DESC": Query.DESCENDING
        }
        self._order_by = (field, dir_map.get(direction.upper(), Query.ASCENDING))
        self._query = self._query.order_by(field, direction=self._order_by[1])
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """Set result limit"""
        self._limit = count
        self._query = self._query.limit(count)
        return self
    
    def offset(self, count: int) -> 'QueryBuilder':
        """Set result offset (inefficient for large offsets)"""
        self._offset = count
        self._query = self._query.offset(count)
        return self
    
    def start_after(self, cursor) -> 'QueryBuilder':
        """Start after cursor (efficient pagination)"""
        self._start_after = cursor
        self._query = self._query.start_after(cursor)
        return self
    
    def select(self, fields: List[str]) -> 'QueryBuilder':
        """Select specific fields only"""
        self._select_fields = fields
        self._query = self._query.select(fields)
        return self
    
    def execute(self) -> QueryResult:
        """Execute query and return results"""
        import time
        start = time.perf_counter()
        
        docs = list(self._query.stream())
        
        results = []
        for doc in docs:
            data = doc.to_dict()
            if data:
                data['id'] = doc.id
                results.append(data)
        
        query_time = (time.perf_counter() - start) * 1000
        
        return QueryResult(
            data=results,
            total_count=len(results),
            has_more=self._limit is not None and len(results) >= self._limit,
            cursor=docs[-1].id if docs and self._limit else None,
            query_time_ms=query_time
        )
    
    def execute_with_cursor(self, page_size: int = 20) -> QueryResult:
        """Execute query with cursor-based pagination"""
        import time
        start = time.perf_counter()
        
        # Request one extra to determine has_more
        self._query = self._query.limit(page_size + 1)
        docs = list(self._query.stream())
        
        has_more = len(docs) > page_size
        if has_more:
            docs = docs[:page_size]
        
        results = []
        for doc in docs:
            data = doc.to_dict()
            if data:
                data['id'] = doc.id
                results.append(data)
        
        query_time = (time.perf_counter() - start) * 1000
        
        return QueryResult(
            data=results,
            has_more=has_more,
            cursor=docs[-1].id if docs else None,
            query_time_ms=query_time
        )
    
    def get_cache_key(self) -> str:
        """Generate cache key for this query"""
        key_parts = [self._collection.id]
        
        for field, op, value in self._filters:
            key_parts.append(f"{field}{op}{value}")
        
        if self._order_by:
            key_parts.append(f"order:{self._order_by[0]}:{self._order_by[1]}")
        
        if self._limit:
            key_parts.append(f"limit:{self._limit}")
        
        if self._offset:
            key_parts.append(f"offset:{self._offset}")
        
        if self._start_after:
            key_parts.append(f"cursor:{self._start_after}")
        
        key_str = ":".join(str(p) for p in key_parts)
        return f"query:{hashlib.md5(key_str.encode()).hexdigest()[:16]}"


class QueryCache:
    """
    In-memory query result cache with TTL
    For frequently repeated queries within short time windows
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 30):
        """
        Initialize query cache
        
        Args:
            max_size: Maximum cached queries
            default_ttl: Default TTL in seconds
        """
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._lock = threading.Lock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result"""
        with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if datetime.utcnow() < expires_at:
                    self._hits += 1
                    return value
                else:
                    del self._cache[key]
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached result"""
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            
            expires_at = datetime.utcnow() + timedelta(seconds=ttl or self._default_ttl)
            self._cache[key] = (value, expires_at)
    
    def invalidate(self, key: str):
        """Invalidate specific key"""
        with self._lock:
            self._cache.pop(key, None)
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate keys matching pattern"""
        with self._lock:
            keys_to_delete = [k for k in self._cache if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]
    
    def clear(self):
        """Clear all cached queries"""
        with self._lock:
            self._cache.clear()
    
    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4)
        }


class BatchQueryExecutor:
    """
    Execute multiple queries in parallel/batch
    Reduces round trips to Firestore
    """
    
    def __init__(self, db):
        """
        Initialize batch executor
        
        Args:
            db: Firestore client instance
        """
        self.db = db
        self._queries: List[Tuple[str, QueryBuilder]] = []
    
    def add(self, name: str, query: QueryBuilder) -> 'BatchQueryExecutor':
        """Add query to batch"""
        self._queries.append((name, query))
        return self
    
    def add_document(self, name: str, collection: str, doc_id: str) -> 'BatchQueryExecutor':
        """Add single document fetch to batch"""
        ref = self.db.collection(collection).document(doc_id)
        self._queries.append((name, ("doc", ref)))
        return self
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute all queries and return results
        
        Returns:
            Dict mapping query names to results
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        start = time.perf_counter()
        results = {}
        
        def execute_query(name: str, query) -> Tuple[str, Any]:
            if isinstance(query, tuple) and query[0] == "doc":
                # Document fetch
                doc = query[1].get()
                if doc.exists:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    return name, data
                return name, None
            else:
                # Query execution
                return name, query.execute()
        
        # Execute in parallel
        with ThreadPoolExecutor(max_workers=min(len(self._queries), 10)) as executor:
            futures = {
                executor.submit(execute_query, name, query): name
                for name, query in self._queries
            }
            
            for future in as_completed(futures):
                try:
                    name, result = future.result()
                    results[name] = result
                except (TypeError, ValueError, RuntimeError) as e:
                    name = futures[future]
                    logger.error("Query %s failed: %s", name, e)
                    results[name] = None
        
        total_time = (time.perf_counter() - start) * 1000
        results['_meta'] = {
            "query_count": len(self._queries),
            "total_time_ms": round(total_time, 2)
        }
        
        return results
    
    def clear(self):
        """Clear pending queries"""
        self._queries.clear()


class OptimizedRepository:
    """
    Mixin class providing optimized query methods for repositories.
    
    This mixin expects the following methods/attributes to be provided
    by the class it's mixed with:
    - get_collection(): Returns Firestore collection reference
    - get_collection_name(): Returns collection name string
    - db: Firestore database client
    """
    
    _query_cache: Optional[QueryCache] = None
    
    # Type hints for mixin - these should be provided by the base class
    def get_collection(self):  # type: ignore
        """Override in subclass - return Firestore collection"""
        raise NotImplementedError("Subclass must implement get_collection()")
    
    def get_collection_name(self) -> str:  # type: ignore
        """Override in subclass - return collection name"""
        raise NotImplementedError("Subclass must implement get_collection_name()")
    
    @classmethod
    def get_query_cache(cls) -> QueryCache:
        """Get or create query cache"""
        if cls._query_cache is None:
            cls._query_cache = QueryCache(max_size=200, default_ttl=30)
        return cls._query_cache
    
    def query_builder(self) -> QueryBuilder:
        """Create query builder for this repository's collection"""
        return QueryBuilder(self.get_collection())
    
    def cached_query(
        self,
        cache_key: str,
        query_func: Callable[[], QueryResult],
        ttl: int = 30
    ) -> QueryResult:
        """
        Execute query with caching
        
        Args:
            cache_key: Cache key for query
            query_func: Function that executes the query
            ttl: Cache TTL in seconds
            
        Returns:
            Query result (from cache or fresh)
        """
        cache = self.get_query_cache()
        
        # Check cache
        cached = cache.get(cache_key)
        if cached is not None:
            cached.cached = True
            return cached
        
        # Execute query
        result = query_func()
        
        # Cache result
        if result.data:
            cache.set(cache_key, result, ttl=ttl)
        
        return result
    
    def paginated_query(
        self,
        filters: Optional[List[Tuple]] = None,
        order_by: Optional[Tuple[str, str]] = None,
        page_size: int = 20,
        cursor: Optional[str] = None,
        cache_ttl: int = 30
    ) -> QueryResult:
        """
        Execute paginated query with caching
        
        Args:
            filters: List of (field, operator, value) tuples
            order_by: Tuple of (field, direction)
            page_size: Results per page
            cursor: Cursor for pagination
            cache_ttl: Cache TTL
            
        Returns:
            QueryResult with pagination info
        """
        # Build query
        builder = self.query_builder()
        
        if filters:
            for field, op, value in filters:
                builder.where(field, op, value)
        
        if order_by:
            builder.order_by(order_by[0], order_by[1])
        
        # Handle cursor
        if cursor:
            cursor_doc = self.get_collection().document(cursor).get()
            if cursor_doc.exists:
                builder.start_after(cursor_doc)
        
        # Generate cache key
        cache_key = f"{self.get_collection_name()}:{builder.get_cache_key()}"
        
        # Execute with caching
        return self.cached_query(
            cache_key=cache_key,
            query_func=lambda: builder.execute_with_cursor(page_size),
            ttl=cache_ttl
        )
    
    def batch_get(self, doc_ids: List[str]) -> Dict[str, Dict]:
        """
        Get multiple documents by ID efficiently
        
        Args:
            doc_ids: List of document IDs
            
        Returns:
            Dict mapping ID to document data
        """
        if not doc_ids:
            return {}
        
        results = {}
        collection = self.get_collection()
        
        # Firestore supports up to 100 docs per getAll
        batch_size = 100
        for i in range(0, len(doc_ids), batch_size):
            batch_ids = doc_ids[i:i + batch_size]
            refs = [collection.document(doc_id) for doc_id in batch_ids]
            
            # Use collection's parent client for get_all
            docs = collection._client.get_all(refs)  # pylint: disable=protected-access
            for doc in docs:
                if doc.exists:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    results[doc.id] = data
        
        return results
    
    def stream_all(
        self,
        filters: Optional[List[Tuple]] = None,
        order_by: Optional[Tuple[str, str]] = None,
        batch_size: int = 500
    ):
        """
        Stream all matching documents in batches
        
        Yields:
            Document data dictionaries
        """
        builder = self.query_builder()
        
        if filters:
            for field, op, value in filters:
                builder.where(field, op, value)
        
        if order_by:
            builder.order_by(order_by[0], order_by[1])
        
        cursor = None
        while True:
            if cursor:
                cursor_doc = self.get_collection().document(cursor).get()
                builder.start_after(cursor_doc)
            
            result = builder.execute_with_cursor(batch_size)
            
            for doc in result.data:
                yield doc
            
            if not result.has_more:
                break
            
            cursor = result.cursor


# =========================================================================
# Query Optimization Utilities
# =========================================================================

def optimize_filters(filters: List[Tuple]) -> List[Tuple]:
    """
    Optimize filter order for Firestore
    
    Firestore performs best when equality filters come before range filters
    
    Args:
        filters: List of (field, operator, value) tuples
        
    Returns:
        Optimized filter list
    """
    equality_ops = {'==', 'in', 'array-contains', 'array-contains-any'}
    
    equality_filters = []
    range_filters = []
    
    for f in filters:
        if f[1] in equality_ops:
            equality_filters.append(f)
        else:
            range_filters.append(f)
    
    return equality_filters + range_filters


def estimate_query_cost(filters: List[Tuple], limit: int = 100) -> Dict[str, Any]:
    """
    Estimate query cost and complexity
    
    Args:
        filters: Query filters
        limit: Query limit
        
    Returns:
        Cost estimation details
    """
    # Base cost: 1 read for the query
    base_reads = 1
    
    # Additional reads for results
    result_reads = limit
    
    # Complexity factors
    has_inequality = any(op not in {'==', 'in'} for _, op, _ in filters)
    filter_count = len(filters)
    
    complexity = "low"
    if has_inequality and filter_count > 2:
        complexity = "high"
    elif has_inequality or filter_count > 3:
        complexity = "medium"
    
    return {
        "estimated_reads": base_reads + result_reads,
        "filter_count": filter_count,
        "has_inequality": has_inequality,
        "complexity": complexity,
        "recommendation": (
            "Consider adding a composite index" 
            if complexity == "high" 
            else "Query is optimized"
        )
    }


# =========================================================================
# Global Query Cache Instance
# =========================================================================

_global_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get global query cache instance"""
    global _global_query_cache  # pylint: disable=global-statement
    if _global_query_cache is None:
        _global_query_cache = QueryCache(max_size=500, default_ttl=30)
    return _global_query_cache


def invalidate_query_cache_for_collection(collection_name: str):
    """Invalidate all cached queries for a collection"""
    cache = get_query_cache()
    cache.invalidate_pattern(collection_name)
