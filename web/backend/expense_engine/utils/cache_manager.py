"""
Cache Manager - Centralized Redis Operations
Enterprise-grade caching for expense_engine
Handles TTL management, key patterns, and connection pooling

Phase 5: Performance Optimization
Phase 6: Enhanced Logging Integration
"""

import json
import logging
import redis
from redis.exceptions import RedisError
from typing import Optional, List, Dict, Any
from datetime import datetime
import threading
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Import operation logger for detailed tracking
try:
    from .operation_logger import (
        log_cache_hit,
        log_cache_miss,
        log_cache_set,
        log_cache_delete
    )
    OPERATION_LOGGING_ENABLED = True
except ImportError:
    OPERATION_LOGGING_ENABLED = False
    def log_cache_hit(key, duration_ms=0, data_size=0): pass
    def log_cache_miss(key, duration_ms=0): pass
    def log_cache_set(key, ttl=0, duration_ms=0, data_size=0): pass
    def log_cache_delete(key, duration_ms=0, pattern=False): pass


class CacheConfig:
    """Cache configuration with optimized TTLs"""
    
    # TTLs (seconds) - Optimized for performance
    TTL_USER = 300  # 5 minutes - user data changes rarely
    TTL_GROUP = 60  # 1 minute - group data moderately stable
    TTL_GROUP_FULL = 30  # 30 seconds - full group with expenses
    TTL_EXPENSES = 30  # 30 seconds - expenses change frequently
    TTL_BALANCE = 15  # 15 seconds - balances need freshness
    TTL_SETTLEMENT = 60  # 1 minute - settlements stable once created
    TTL_INVITATION = 120  # 2 minutes - invitations change rarely
    TTL_USER_GROUPS = 60  # 1 minute - user's groups list
    TTL_ANALYTICS = 300  # 5 minutes - analytics data
    
    # Short TTLs for frequently changing data
    TTL_SHORT = 15  # 15 seconds
    TTL_MEDIUM = 60  # 1 minute
    TTL_LONG = 300  # 5 minutes
    TTL_VERY_LONG = 3600  # 1 hour
    
    # Key prefixes - all expense_engine keys use this prefix
    PREFIX_BASE = "expense:"
    PREFIX_USER = "expense:user:"
    PREFIX_GROUP = "expense:group:"
    PREFIX_GROUP_FULL = "expense:group_full:"
    PREFIX_EXPENSES = "expense:expenses:"
    PREFIX_BALANCE = "expense:balance:"
    PREFIX_SETTLEMENT = "expense:settlement:"
    PREFIX_INVITATION = "expense:invitation:"
    PREFIX_USER_GROUPS = "expense:user_groups:"
    PREFIX_USER_INVITATIONS = "expense:user_invites:"
    PREFIX_ANALYTICS = "expense:analytics:"
    PREFIX_LOCK = "expense:lock:"
    PREFIX_RATE_LIMIT = "expense:ratelimit:"


class CacheStats:
    """Thread-safe cache statistics tracker"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._errors = 0
        self._sets = 0
        self._deletes = 0
        self._start_time = datetime.utcnow()
    
    def record_hit(self):
        with self._lock:
            self._hits += 1
    
    def record_miss(self):
        with self._lock:
            self._misses += 1
    
    def record_error(self):
        with self._lock:
            self._errors += 1
    
    def record_set(self):
        with self._lock:
            self._sets += 1
    
    def record_delete(self):
        with self._lock:
            self._deletes += 1
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all statistics"""
        with self._lock:
            total_ops = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "errors": self._errors,
                "sets": self._sets,
                "deletes": self._deletes,
                "hit_rate": self.hit_rate,
                "total_operations": total_ops,
                "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds()
            }
    
    def reset(self):
        """Reset all counters"""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._errors = 0
            self._sets = 0
            self._deletes = 0
            self._start_time = datetime.utcnow()


class CacheManager:
    """
    Centralized Redis cache manager for expense_engine
    
    Features:
    - Connection pooling with health checks
    - Automatic TTL management
    - Cache statistics tracking
    - Distributed locking
    - Graceful degradation when Redis unavailable
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern for connection reuse"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True
    ):
        """
        Initialize cache manager with Redis connection pool
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            max_connections: Maximum pool connections
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
            retry_on_timeout: Retry on timeout
        """
        if self._initialized:  # pylint: disable=access-member-before-definition
            return
        
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        
        self._redis_client: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None
        self._stats = CacheStats()
        self._connected = False
        
        self._initialize_connection()
        self._initialized = True
    
    def _initialize_connection(self):
        """Initialize Redis connection with connection pool"""
        try:
            # Create connection pool
            self._pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=self.retry_on_timeout,
                decode_responses=True,
                health_check_interval=30
            )
            
            # Create client with pool
            self._redis_client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            self._redis_client.ping()
            self._connected = True
            
            logger.info("Redis cache manager initialized successfully")
            logger.info("  Host: %s:%d", self.host, self.port)
            logger.info("  Max connections: %d", self.max_connections)
            
        except redis.ConnectionError as e:
            logger.warning("Redis connection failed: %s", str(e))
            logger.warning("Cache will operate in degraded mode (no caching)")
            self._redis_client = None
            self._pool = None
            self._connected = False
        except RedisError as e:
            logger.error("Failed to initialize cache manager: %s", str(e))
            self._redis_client = None
            self._pool = None
            self._connected = False
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        if not self._redis_client:
            return False
        try:
            self._redis_client.ping()
            return True
        except RedisError:
            self._connected = False
            return False
    
    def reconnect(self) -> bool:
        """Attempt to reconnect to Redis"""
        logger.info("Attempting Redis reconnection...")
        self._initialize_connection()
        return self._connected
    
    # =========================================================================
    # Core Cache Operations
    # =========================================================================
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.is_available():
            self._stats.record_miss()
            log_cache_miss(key)
            return None
        
        start_time = time.time()
        try:
            value = self._redis_client.get(key)
            duration_ms = (time.time() - start_time) * 1000
            
            if value is not None:
                self._stats.record_hit()
                try:
                    parsed = json.loads(value)
                    log_cache_hit(key, duration_ms, len(value))
                    return parsed
                except json.JSONDecodeError:
                    log_cache_hit(key, duration_ms, len(value) if value else 0)
                    return value
            
            self._stats.record_miss()
            log_cache_miss(key, duration_ms)
            return None
        except RedisError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Cache GET error for %s: %s", key, str(e))
            self._stats.record_error()
            log_cache_miss(key, duration_ms)
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
            
        Returns:
            True if set successfully
        """
        if not self.is_available():
            return False
        
        start_time = time.time()
        try:
            # Serialize value
            if not isinstance(value, str):
                serialized = json.dumps(value, default=str)
            else:
                serialized = value
            
            # Set with optional flags
            if ttl:
                result = self._redis_client.set(key, serialized, ex=ttl, nx=nx, xx=xx)
            else:
                result = self._redis_client.set(key, serialized, nx=nx, xx=xx)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if result:
                self._stats.record_set()
                log_cache_set(key, ttl or 0, duration_ms, len(serialized))
            return bool(result)
        except RedisError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Cache SET error for %s: %s", key, str(e))
            self._stats.record_error()
            return False
    
    def delete(self, *keys: str) -> int:
        """
        Delete keys from cache
        
        Args:
            keys: Keys to delete
            
        Returns:
            Number of keys deleted
        """
        if not self.is_available() or not keys:
            return 0
        
        start_time = time.time()
        try:
            count = self._redis_client.delete(*keys)
            duration_ms = (time.time() - start_time) * 1000
            
            self._stats.record_delete()
            for key in keys:
                log_cache_delete(key, duration_ms / len(keys))
            return count
        except RedisError as e:
            logger.error("Cache DELETE error: %s", str(e))
            self._stats.record_error()
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.is_available():
            return False
        try:
            return bool(self._redis_client.exists(key))
        except RedisError:
            return False
    
    def ttl(self, key: str) -> int:
        """Get remaining TTL for key"""
        if not self.is_available():
            return -2
        try:
            return self._redis_client.ttl(key)
        except RedisError:
            return -2
    
    def expire(self, key: str, ttl: int) -> bool:
        """Update TTL for existing key"""
        if not self.is_available():
            return False
        try:
            return bool(self._redis_client.expire(key, ttl))
        except RedisError:
            return False
    
    # =========================================================================
    # Batch Operations
    # =========================================================================
    
    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values at once
        
        Args:
            keys: List of keys
            
        Returns:
            Dict of key -> value (excludes missing keys)
        """
        if not self.is_available() or not keys:
            return {}
        
        try:
            values = self._redis_client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                        self._stats.record_hit()
                    except json.JSONDecodeError:
                        result[key] = value
                        self._stats.record_hit()
                else:
                    self._stats.record_miss()
            return result
        except RedisError as e:
            logger.error("Cache MGET error: %s", str(e))
            self._stats.record_error()
            return {}
    
    def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple values at once
        
        Args:
            mapping: Dict of key -> value
            ttl: Optional TTL for all keys
            
        Returns:
            True if successful
        """
        if not self.is_available() or not mapping:
            return False
        
        try:
            # Serialize values
            serialized = {
                k: json.dumps(v, default=str) if not isinstance(v, str) else v
                for k, v in mapping.items()
            }
            
            # Use pipeline for atomic operation
            pipe = self._redis_client.pipeline()
            for key, value in serialized.items():
                if ttl:
                    pipe.setex(key, ttl, value)
                else:
                    pipe.set(key, value)
            pipe.execute()
            
            self._stats.record_set()
            return True
        except RedisError as e:
            logger.error("Cache MSET error: %s", str(e))
            self._stats.record_error()
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern
        
        Args:
            pattern: Redis pattern (e.g., "expense:group:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.is_available():
            return 0
        
        try:
            keys = list(self._redis_client.scan_iter(match=pattern))
            if keys:
                return self._redis_client.delete(*keys)
            return 0
        except RedisError as e:
            logger.error("Cache DELETE_PATTERN error for %s: %s", pattern, str(e))
            self._stats.record_error()
            return 0
    
    # =========================================================================
    # Domain-Specific Operations
    # =========================================================================
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get cached user data"""
        key = f"{CacheConfig.PREFIX_USER}{user_id}"
        return self.get(key)
    
    def set_user(self, user_id: str, data: Dict) -> bool:
        """Cache user data"""
        key = f"{CacheConfig.PREFIX_USER}{user_id}"
        return self.set(key, data, ttl=CacheConfig.TTL_USER)
    
    def get_group(self, group_id: str) -> Optional[Dict]:
        """Get cached group data"""
        key = f"{CacheConfig.PREFIX_GROUP}{group_id}"
        return self.get(key)
    
    def set_group(self, group_id: str, data: Dict) -> bool:
        """Cache group data"""
        key = f"{CacheConfig.PREFIX_GROUP}{group_id}"
        return self.set(key, data, ttl=CacheConfig.TTL_GROUP)
    
    def get_group_full(self, group_id: str) -> Optional[Dict]:
        """Get cached full group data (with expenses, members, balances)"""
        key = f"{CacheConfig.PREFIX_GROUP_FULL}{group_id}"
        return self.get(key)
    
    def set_group_full(self, group_id: str, data: Dict) -> bool:
        """Cache full group data"""
        key = f"{CacheConfig.PREFIX_GROUP_FULL}{group_id}"
        return self.set(key, data, ttl=CacheConfig.TTL_GROUP_FULL)
    
    def get_balances(self, group_id: str) -> Optional[Dict]:
        """Get cached group balances"""
        key = f"{CacheConfig.PREFIX_BALANCE}{group_id}"
        return self.get(key)
    
    def set_balances(self, group_id: str, data: Dict) -> bool:
        """Cache group balances"""
        key = f"{CacheConfig.PREFIX_BALANCE}{group_id}"
        return self.set(key, data, ttl=CacheConfig.TTL_BALANCE)
    
    def get_user_groups(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached user's groups list"""
        key = f"{CacheConfig.PREFIX_USER_GROUPS}{user_id}"
        return self.get(key)
    
    def set_user_groups(self, user_id: str, groups: List[Dict]) -> bool:
        """Cache user's groups list"""
        key = f"{CacheConfig.PREFIX_USER_GROUPS}{user_id}"
        return self.set(key, groups, ttl=CacheConfig.TTL_USER_GROUPS)
    
    def get_user_invitations(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached user's invitations"""
        key = f"{CacheConfig.PREFIX_USER_INVITATIONS}{user_id}"
        return self.get(key)
    
    def set_user_invitations(self, user_id: str, invitations: List[Dict]) -> bool:
        """Cache user's invitations"""
        key = f"{CacheConfig.PREFIX_USER_INVITATIONS}{user_id}"
        return self.set(key, invitations, ttl=CacheConfig.TTL_INVITATION)
    
    # =========================================================================
    # Invalidation Operations
    # =========================================================================
    
    def invalidate_group(self, group_id: str) -> int:
        """
        Invalidate all caches related to a group
        
        Args:
            group_id: Group ID
            
        Returns:
            Number of keys invalidated
        """
        keys = [
            f"{CacheConfig.PREFIX_GROUP}{group_id}",
            f"{CacheConfig.PREFIX_GROUP_FULL}{group_id}",
            f"{CacheConfig.PREFIX_EXPENSES}{group_id}",
            f"{CacheConfig.PREFIX_BALANCE}{group_id}",
            f"{CacheConfig.PREFIX_SETTLEMENT}{group_id}",
        ]
        count = self.delete(*keys)
        logger.debug("Invalidated %d cache keys for group %s", count, group_id)
        return count
    
    def invalidate_user_groups(self, user_id: str) -> int:
        """
        Invalidate user's groups list cache
        
        Args:
            user_id: User ID
            
        Returns:
            Number of keys invalidated
        """
        key = f"{CacheConfig.PREFIX_USER_GROUPS}{user_id}"
        return self.delete(key)
    
    def invalidate_user(self, user_id: str) -> int:
        """
        Invalidate all caches for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of keys invalidated
        """
        keys = [
            f"{CacheConfig.PREFIX_USER}{user_id}",
            f"{CacheConfig.PREFIX_USER_GROUPS}{user_id}",
            f"{CacheConfig.PREFIX_USER_INVITATIONS}{user_id}",
        ]
        return self.delete(*keys)
    
    def invalidate_all_group_members(self, member_ids: List[str]) -> int:
        """
        Invalidate user_groups cache for all members of a group
        
        Args:
            member_ids: List of member user IDs
            
        Returns:
            Number of keys invalidated
        """
        if not member_ids:
            return 0
        
        keys = [f"{CacheConfig.PREFIX_USER_GROUPS}{uid}" for uid in member_ids]
        return self.delete(*keys)
    
    # =========================================================================
    # Distributed Locking
    # =========================================================================
    
    @contextmanager
    def lock(
        self,
        name: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: int = 5
    ):
        """
        Distributed lock using Redis
        
        Args:
            name: Lock name
            timeout: Lock auto-release timeout
            blocking: Whether to block waiting for lock
            blocking_timeout: How long to wait for lock
            
        Yields:
            True if lock acquired, False otherwise
        """
        if not self.is_available():
            yield True  # Degrade gracefully
            return
        
        lock_key = f"{CacheConfig.PREFIX_LOCK}{name}"
        lock = self._redis_client.lock(
            lock_key,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout
        )
        
        acquired = False
        try:
            acquired = lock.acquire()
            yield acquired
        finally:
            if acquired:
                try:
                    lock.release()
                except RedisError:
                    pass  # Lock may have expired
    
    # =========================================================================
    # Statistics and Health
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self._stats.get_stats()
        stats["connected"] = self._connected
        stats["available"] = self.is_available()
        return stats
    
    def reset_stats(self):
        """Reset statistics"""
        self._stats.reset()
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis server info"""
        if not self.is_available():
            return {"error": "Redis not available"}
        
        try:
            info = self._redis_client.info()
            return {
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_connections_received": info.get("total_connections_received"),
                "keyspace": info.get("db0", {}),
            }
        except RedisError as e:
            return {"error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        result = {
            "status": "healthy" if self.is_available() else "unhealthy",
            "connected": self._connected,
            "stats": self.get_stats()
        }
        
        if self.is_available():
            try:
                # Measure latency
                start = datetime.utcnow()
                self._redis_client.ping()
                latency = (datetime.utcnow() - start).total_seconds() * 1000
                result["latency_ms"] = round(latency, 2)
            except RedisError as e:
                result["status"] = "degraded"
                result["error"] = str(e)
        
        return result


# =========================================================================
# Global Cache Manager Instance
# =========================================================================

_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    Get the global cache manager instance
    
    Returns:
        CacheManager singleton instance
    """
    global _cache_manager  # pylint: disable=global-statement
    if _cache_manager is None:
        # Load from config
        try:
            from ..config import redis_config
            _cache_manager = CacheManager(
                host=redis_config.HOST,
                port=redis_config.PORT,
                db=redis_config.DB,
                password=redis_config.PASSWORD,
                max_connections=redis_config.MAX_CONNECTIONS,
                socket_timeout=redis_config.SOCKET_TIMEOUT
            )
        except ImportError:
            # Fallback to defaults
            _cache_manager = CacheManager()
    
    return _cache_manager


def invalidate_cache_for_expense_change(
    group_id: str,
    member_ids: Optional[List[str]] = None
):
    """
    Convenience function to invalidate caches after expense changes
    
    Args:
        group_id: Group ID where expense changed
        member_ids: Optional list of member IDs to invalidate
    """
    cache = get_cache_manager()
    cache.invalidate_group(group_id)
    
    if member_ids:
        cache.invalidate_all_group_members(member_ids)


def generate_cache_key(*parts: str) -> str:
    """
    Generate a cache key from parts
    
    Args:
        parts: Key parts to join
        
    Returns:
        Joined cache key
    """
    return ":".join(str(p) for p in parts if p)
