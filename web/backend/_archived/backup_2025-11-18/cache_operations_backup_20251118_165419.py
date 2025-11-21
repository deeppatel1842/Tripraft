"""
Group Planner Cache Operations
Redis caching operations for group planner system
Following expense engine architecture patterns for optimal performance
"""

import json
import logging
import redis
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .config import RedisConfig, get_cache_key, get_cache_ttl

logger = logging.getLogger(__name__)


class GroupPlannerCacheOperations:
    """Redis caching operations for group planner system"""
    
    def __init__(self, redis_url: str = None, max_connections: int = None):
        """
        Initialize Redis cache service
        Args:
            redis_url: Redis connection URL (default from config)
            max_connections: Maximum connection pool size (default from config)
        """
        self.redis_client = None
        self.redis_pool = None
        self.redis_url = redis_url or RedisConfig.DEFAULT_URL
        self.max_connections = max_connections or RedisConfig.MAX_CONNECTIONS
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis with optimized connection pool"""
        try:
            logger.info("🔄 Initializing Group Planner Redis cache...")
            logger.info("   URL: %s", self.redis_url)
            
            # Create connection pool
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                socket_timeout=RedisConfig.SOCKET_TIMEOUT,
                socket_connect_timeout=RedisConfig.SOCKET_TIMEOUT,
                retry_on_timeout=True,
                decode_responses=True  # Automatically decode responses to strings
            )
            
            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            # Test connection
            self.redis_client.ping()
            
            logger.info("✅ Group Planner Redis cache initialized successfully")
            logger.info("   Max connections: %s", self.max_connections)
            logger.info("   Socket timeout: %ss", RedisConfig.SOCKET_TIMEOUT)
            logger.info("   Connection pooling: ENABLED")
            
        except ConnectionError as e:
            logger.warning("⚠️  Redis connection failed: %s", e)
            logger.warning("📝 To fix: Install and start Redis server")
            logger.warning("   Windows: Download from https://github.com/microsoftarchive/redis/releases")
            logger.warning("   Or use Docker: docker run -d -p 6379:6379 redis:alpine")
            logger.warning("   Or use WSL: sudo apt install redis-server && sudo service redis-server start")
            self.redis_client = None
            self.redis_pool = None
        except Exception as e:
            logger.error("❌ Failed to initialize Redis cache: %s", e)
            self.redis_client = None
            self.redis_pool = None
    
    def _is_available(self) -> bool:
        """Check if Redis is available"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def _safe_json_loads(self, data: str) -> Optional[Any]:
        """Safely parse JSON data"""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def _safe_json_dumps(self, data: Any) -> str:
        """Safely serialize data to JSON"""
        try:
            return json.dumps(data, default=str)  # Convert datetime to string
        except (TypeError, ValueError):
            return "{}"
    
    # =========================================================================
    # GROUP CACHE OPERATIONS
    # =========================================================================
    
    def cache_group(self, group_id: str, group_data: Dict) -> bool:
        """Cache group data"""
        if not self._is_available():
            return False
        
        try:
            key = get_cache_key('GROUP', group_id)
            json_data = self._safe_json_dumps(group_data)
            ttl = get_cache_ttl('GROUP')
            self.redis_client.setex(key, ttl, json_data)
            logger.debug("Cached group: %s", group_id)
            return True
        except Exception as e:
            logger.warning("Failed to cache group %s: %s", group_id, e)
            return False
    
    def get_cached_group(self, group_id: str) -> Optional[Dict]:
        """Get cached group data"""
        if not self._is_available():
            return None
        
        try:
            key = get_cache_key('GROUP', group_id)
            data = self.redis_client.get(key)
            if data:
                logger.debug("Cache HIT: group %s", group_id)
                return self._safe_json_loads(data)
            else:
                logger.debug("Cache MISS: group %s", group_id)
                return None
        except Exception as e:
            logger.warning("Failed to get cached group %s: %s", group_id, e)
            return None
    
    def invalidate_group(self, group_id: str) -> bool:
        """Invalidate group cache"""
        if not self._is_available():
            return False
        
        try:
            keys_to_delete = [
                f"groupplanner:group:{group_id}",
                f"groupplanner:group_members:{group_id}",
                f"groupplanner:group_places:{group_id}",
                f"groupplanner:group_polls:{group_id}"
            ]
            
            # Also invalidate user_groups cache for all group members
            group_data = self.get_cached_group(group_id)
            if group_data and group_data.get('members'):
                for member_id in group_data['members']:
                    keys_to_delete.append(f"groupplanner:user_groups:{member_id}")
            
            deleted_count = self.redis_client.delete(*keys_to_delete)
            logger.debug("Invalidated group %s cache: %s keys", group_id, deleted_count)
            return True
        except Exception as e:
            logger.warning("Failed to invalidate group %s cache: %s", group_id, e)
            return False
    
    def cache_user_groups(self, user_id: str, groups: List[Dict]) -> bool:
        """Cache user's groups list"""
        if not self._is_available():
            return False
        
        try:
            key = get_cache_key('USER_GROUPS', user_id)
            json_data = self._safe_json_dumps(groups)
            ttl = get_cache_ttl('USER_GROUPS')
            self.redis_client.setex(key, ttl, json_data)
            logger.debug("Cached user groups: %s (%s groups)", user_id, len(groups))
            return True
        except Exception as e:
            logger.warning("Failed to cache user groups %s: %s", user_id, e)
            return False
    
    def get_cached_user_groups(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached user groups"""
        if not self._is_available():
            return None
        
        try:
            key = get_cache_key('USER_GROUPS', user_id)
            data = self.redis_client.get(key)
            if data:
                logger.debug("Cache HIT: user groups %s", user_id)
                return self._safe_json_loads(data)
            else:
                logger.debug("Cache MISS: user groups %s", user_id)
                return None
        except Exception as e:
            logger.warning("Failed to get cached user groups %s: %s", user_id, e)
            return None
    
    def invalidate_user_groups(self, user_id: str) -> bool:
        """Invalidate user groups cache"""
        if not self._is_available():
            return False
        
        try:
            key = f"groupplanner:user_groups:{user_id}"
            self.redis_client.delete(key)
            logger.debug("Invalidated user groups cache: %s", user_id)
            return True
        except Exception as e:
            logger.warning("Failed to invalidate user groups %s: %s", user_id, e)
            return False
    
    # =========================================================================
    # GROUP MEMBERS CACHE OPERATIONS
    # =========================================================================
    
    def cache_group_members(self, group_id: str, members: List[Dict]) -> bool:
        """Cache group members list"""
        if not self._is_available():
            return False
        
        try:
            key = get_cache_key('GROUP_MEMBERS', group_id)
            json_data = self._safe_json_dumps(members)
            ttl = get_cache_ttl('GROUP_MEMBERS')
            self.redis_client.setex(key, ttl, json_data)
            logger.debug("Cached group members: %s (%s members)", group_id, len(members))
            return True
        except Exception as e:
            logger.warning("Failed to cache group members %s: %s", group_id, e)
            return False
    
    def get_cached_group_members(self, group_id: str) -> Optional[List[Dict]]:
        """Get cached group members"""
        if not self._is_available():
            return None
        
        try:
            key = f"groupplanner:group_members:{group_id}"
            data = self.redis_client.get(key)
            if data:
                logger.debug("Cache HIT: group members %s", group_id)
                return self._safe_json_loads(data)
            else:
                logger.debug("Cache MISS: group members %s", group_id)
                return None
        except Exception as e:
            logger.warning("Failed to get cached group members %s: %s", group_id, e)
            return None
    
    def invalidate_group_members(self, group_id: str) -> bool:
        """Invalidate group members cache"""
        if not self._is_available():
            return False
        
        try:
            key = f"groupplanner:group_members:{group_id}"
            self.redis_client.delete(key)
            logger.debug("Invalidated group members cache: %s", group_id)
            return True
        except Exception as e:
            logger.warning("Failed to invalidate group members %s: %s", group_id, e)
            return False
    
    # =========================================================================
    # GROUP PLACES CACHE OPERATIONS
    # =========================================================================
    
    def cache_group_places(self, group_id: str, places: List[Dict]) -> bool:
        """Cache group places list"""
        if not self._is_available():
            return False
        
        try:
            key = get_cache_key('GROUP_PLACES', group_id)
            json_data = self._safe_json_dumps(places)
            ttl = get_cache_ttl('GROUP_PLACES')
            self.redis_client.setex(key, ttl, json_data)
            logger.debug("Cached group places: %s (%s places)", group_id, len(places))
            return True
        except Exception as e:
            logger.warning("Failed to cache group places %s: %s", group_id, e)
            return False
    
    def get_cached_group_places(self, group_id: str) -> Optional[List[Dict]]:
        """Get cached group places"""
        if not self._is_available():
            return None
        
        try:
            key = f"groupplanner:group_places:{group_id}"
            data = self.redis_client.get(key)
            if data:
                logger.debug("Cache HIT: group places %s", group_id)
                return self._safe_json_loads(data)
            else:
                logger.debug("Cache MISS: group places %s", group_id)
                return None
        except Exception as e:
            logger.warning("Failed to get cached group places %s: %s", group_id, e)
            return None
    
    def invalidate_group_places(self, group_id: str) -> bool:
        """Invalidate group places cache"""
        if not self._is_available():
            return False
        
        try:
            key = f"groupplanner:group_places:{group_id}"
            self.redis_client.delete(key)
            logger.debug("Invalidated group places cache: %s", group_id)
            return True
        except Exception as e:
            logger.warning("Failed to invalidate group places %s: %s", group_id, e)
            return False
    
    # =========================================================================
    # GROUP POLLS CACHE OPERATIONS
    # =========================================================================
    
    def cache_group_polls(self, group_id: str, polls: List[Dict]) -> bool:
        """Cache group polls list"""
        if not self._is_available():
            return False
        
        try:
            key = get_cache_key('GROUP_POLLS', group_id)
            json_data = self._safe_json_dumps(polls)
            ttl = get_cache_ttl('GROUP_POLLS')
            self.redis_client.setex(key, ttl, json_data)
            logger.debug("Cached group polls: %s (%s polls)", group_id, len(polls))
            return True
        except Exception as e:
            logger.warning("Failed to cache group polls %s: %s", group_id, e)
            return False
    
    def get_cached_group_polls(self, group_id: str) -> Optional[List[Dict]]:
        """Get cached group polls"""
        if not self._is_available():
            return None
        
        try:
            key = f"groupplanner:group_polls:{group_id}"
            data = self.redis_client.get(key)
            if data:
                logger.debug("Cache HIT: group polls %s", group_id)
                return self._safe_json_loads(data)
            else:
                logger.debug("Cache MISS: group polls %s", group_id)
                return None
        except Exception as e:
            logger.warning("Failed to get cached group polls %s: %s", group_id, e)
            return None
    
    def invalidate_group_polls(self, group_id: str) -> bool:
        """Invalidate group polls cache"""
        if not self._is_available():
            return False
        
        try:
            key = f"groupplanner:group_polls:{group_id}"
            self.redis_client.delete(key)
            logger.debug("Invalidated group polls cache: %s", group_id)
            return True
        except Exception as e:
            logger.warning("Failed to invalidate group polls %s: %s", group_id, e)
            return False
    
    # =========================================================================
    # USER INVITATIONS CACHE OPERATIONS
    # =========================================================================
    
    def cache_user_invitations(self, user_id: str, invitations: List[Dict]) -> bool:
        """Cache user invitations list"""
        if not self._is_available():
            return False
        
        try:
            key = get_cache_key('USER_INVITATIONS', user_id)
            json_data = self._safe_json_dumps(invitations)
            ttl = get_cache_ttl('USER_INVITATIONS')
            self.redis_client.setex(key, ttl, json_data)
            logger.debug("Cached user invitations: %s (%s invitations)", user_id, len(invitations))
            return True
        except Exception as e:
            logger.warning("Failed to cache user invitations %s: %s", user_id, e)
            return False
    
    def get_cached_user_invitations(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached user invitations"""
        if not self._is_available():
            return None
        
        try:
            key = f"groupplanner:user_invitations:{user_id}"
            data = self.redis_client.get(key)
            if data:
                logger.debug("Cache HIT: user invitations %s", user_id)
                return self._safe_json_loads(data)
            else:
                logger.debug("Cache MISS: user invitations %s", user_id)
                return None
        except Exception as e:
            logger.warning("Failed to get cached user invitations %s: %s", user_id, e)
            return None
    
    def invalidate_user_invitations(self, user_id: str) -> bool:
        """Invalidate user invitations cache"""
        if not self._is_available():
            return False
        
        try:
            key = f"groupplanner:user_invitations:{user_id}"
            self.redis_client.delete(key)
            logger.debug("Invalidated user invitations cache: %s", user_id)
            return True
        except Exception as e:
            logger.warning("Failed to invalidate user invitations %s: %s", user_id, e)
            return False
    
    # =========================================================================
    # USER CACHE OPERATIONS
    # =========================================================================
    
    def cache_user(self, user_id: str, user_data: Dict) -> bool:
        """Cache user profile data"""
        if not self._is_available():
            return False
        
        try:
            key = get_cache_key('USER_PROFILE', user_id)
            json_data = self._safe_json_dumps(user_data)
            ttl = get_cache_ttl('USER_PROFILE')
            self.redis_client.setex(key, ttl, json_data)
            logger.debug("Cached user: %s", user_id)
            return True
        except Exception as e:
            logger.warning("Failed to cache user %s: %s", user_id, e)
            return False
    
    def get_cached_user(self, user_id: str) -> Optional[Dict]:
        """Get cached user profile data"""
        if not self._is_available():
            return None
        
        try:
            key = f"groupplanner:user:{user_id}"
            data = self.redis_client.get(key)
            if data:
                logger.debug("Cache HIT: user %s", user_id)
                return self._safe_json_loads(data)
            else:
                logger.debug("Cache MISS: user %s", user_id)
                return None
        except Exception as e:
            logger.warning("Failed to get cached user %s: %s", user_id, e)
            return None
    
    def invalidate_user(self, user_id: str) -> bool:
        """Invalidate user cache"""
        if not self._is_available():
            return False
        
        try:
            key = f"groupplanner:user:{user_id}"
            self.redis_client.delete(key)
            logger.debug("Invalidated user cache: %s", user_id)
            return True
        except Exception as e:
            logger.warning("Failed to invalidate user %s: %s", user_id, e)
            return False

    def cache_invitation(self, invitation_id: str, invitation_data: Dict) -> bool:
        """Cache invitation data"""
        if not self._is_available():
            return False
        
        try:
            key = f"groupplanner:invitation:{invitation_id}"
            ttl = RedisConfig.CACHE_TTL.get('invitations', 3600)
            self.redis_client.setex(key, ttl, json.dumps(invitation_data, default=str))
            logger.debug("Cached invitation: %s", invitation_id)
            return True
        except Exception as e:
            logger.warning("Failed to cache invitation %s: %s", invitation_id, e)
            return False

    def get_cached_invitation(self, invitation_id: str) -> Optional[Dict]:
        """Get cached invitation"""
        if not self._is_available():
            return None
        
        try:
            key = f"groupplanner:invitation:{invitation_id}"
            data = self.redis_client.get(key)
            if data:
                logger.debug("Cache HIT: invitation %s", invitation_id)
                return json.loads(data)
            logger.debug("Cache MISS: invitation %s", invitation_id)
            return None
        except Exception as e:
            logger.warning("Failed to get cached invitation %s: %s", invitation_id, e)
            return None

    def invalidate_invitation(self, invitation_id: str) -> bool:
        """Invalidate invitation cache"""
        if not self._is_available():
            return False
        
        try:
            key = f"groupplanner:invitation:{invitation_id}"
            self.redis_client.delete(key)
            logger.debug("Invalidated invitation cache: %s", invitation_id)
            return True
        except Exception as e:
            logger.warning("Failed to invalidate invitation %s: %s", invitation_id, e)
            return False

    def cache_group_invitations(self, group_id: str, invitations: List[Dict]) -> bool:
        """Cache group invitations"""
        if not self._is_available():
            return False
        
        try:
            key = f"groupplanner:group_invitations:{group_id}"
            ttl = RedisConfig.CACHE_TTL.get('invitations', 3600)
            self.redis_client.setex(key, ttl, json.dumps(invitations, default=str))
            logger.debug("Cached group invitations: %s", group_id)
            return True
        except Exception as e:
            logger.warning("Failed to cache group invitations %s: %s", group_id, e)
            return False

    def get_cached_group_invitations(self, group_id: str) -> Optional[List[Dict]]:
        """Get cached group invitations"""
        if not self._is_available():
            return None
        
        try:
            key = f"groupplanner:group_invitations:{group_id}"
            data = self.redis_client.get(key)
            if data:
                logger.debug("Cache HIT: group_invitations %s", group_id)
                return json.loads(data)
            logger.debug("Cache MISS: group_invitations %s", group_id)
            return None
        except Exception as e:
            logger.warning("Failed to get cached group invitations %s: %s", group_id, e)
            return None

    def invalidate_group_invitations(self, group_id: str) -> bool:
        """Invalidate group invitations cache"""
        if not self._is_available():
            return False
        
        try:
            key = f"groupplanner:group_invitations:{group_id}"
            self.redis_client.delete(key)
            logger.debug("Invalidated group invitations cache: %s", group_id)
            return True
        except Exception as e:
            logger.warning("Failed to invalidate group invitations %s: %s", group_id, e)
            return False
    
    # =========================================================================
    # CACHE MANAGEMENT & UTILITIES
    # =========================================================================
    
    def clear_user_related_cache(self, user_id: str) -> bool:
        """Clear all cache entries related to a specific user"""
        if not self._is_available():
            return False
        
        try:
            pattern = f"groupplanner:*{user_id}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info("Cleared user cache: %s (%s keys)", user_id, deleted_count)
            return True
        except Exception as e:
            logger.warning("Failed to clear user cache %s: %s", user_id, e)
            return False
    
    def clear_group_related_cache(self, group_id: str) -> bool:
        """Clear all cache entries related to a specific group"""
        if not self._is_available():
            return False
        
        try:
            pattern = f"groupplanner:*{group_id}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info("Cleared group cache: %s (%s keys)", group_id, deleted_count)
            return True
        except Exception as e:
            logger.warning("Failed to clear group cache %s: %s", group_id, e)
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._is_available():
            return {"available": False}
        
        try:
            info = self.redis_client.info()
            stats = {
                "available": True,
                "connected_clients": info.get('connected_clients', 0),
                "used_memory": info.get('used_memory_human', '0B'),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0)
            }
            
            # Calculate hit ratio
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            if hits + misses > 0:
                stats["hit_ratio"] = round(hits / (hits + misses) * 100, 2)
            else:
                stats["hit_ratio"] = 0
            
            # Count group planner keys
            pattern = "groupplanner:*"
            stats["groupplanner_keys"] = len(self.redis_client.keys(pattern))
            
            return stats
        except Exception as e:
            logger.warning("Failed to get cache stats: %s", e)
            return {"available": False, "error": str(e)}
    
    def health_check(self) -> bool:
        """Check Redis health"""
        try:
            if not self._is_available():
                return False
            
            # Test basic operations
            test_key = "groupplanner:health_check"
            self.redis_client.setex(test_key, 10, "ok")
            result = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            return result == "ok"
        except Exception as e:
            logger.warning("Redis health check failed: %s", e)
            return False
    
    # =========================================================================
    # GENERIC CACHE OPERATIONS (for idempotency, etc.)
    # =========================================================================
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache by key"""
        if not self._is_available():
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return value
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.warning(f"Failed to get cache key {key}: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        if not self._is_available():
            return False
        
        try:
            self.redis_client.setex(key, ttl, value)
            logger.debug(f"Cached {key} with TTL {ttl}s")
            return True
        except Exception as e:
            logger.warning(f"Failed to set cache key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self._is_available():
            return False
        
        try:
            result = self.redis_client.delete(key)
            logger.debug(f"Deleted cache key {key}: {result}")
            return result > 0
        except Exception as e:
            logger.warning(f"Failed to delete cache key {key}: {e}")
            return False
    
    # =========================================================================
    # METRICS AND MONITORING (Phase 4)
    # =========================================================================
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics for monitoring
        Returns metrics about cache usage, memory, and performance
        """
        if not self._is_available():
            return {
                'available': False,
                'error': 'Redis not connected'
            }
        
        try:
            # Get Redis INFO command output
            info = self.redis_client.info()
            
            # Get key counts by pattern
            key_patterns = {
                'groups': 'groupplanner:group:*',
                'user_groups': 'groupplanner:user_groups:*',
                'places': 'groupplanner:group_places:*',
                'polls': 'groupplanner:group_polls:*',
                'members': 'groupplanner:group_members:*',
                'invitations': 'groupplanner:user_invitations:*'
            }
            
            key_counts = {}
            for name, pattern in key_patterns.items():
                try:
                    # Use SCAN for large key sets (more efficient than KEYS)
                    cursor = 0
                    count = 0
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                        count += len(keys)
                        if cursor == 0:
                            break
                    key_counts[name] = count
                except Exception as e:
                    logger.warning(f"Failed to count keys for {name}: {e}")
                    key_counts[name] = 0
            
            # Calculate cache metrics
            stats = {
                'available': True,
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'Unknown'),
                'used_memory_bytes': info.get('used_memory', 0),
                'used_memory_peak_human': info.get('used_memory_peak_human', 'Unknown'),
                'total_keys': sum(key_counts.values()),
                'keys_by_type': key_counts,
                'redis_version': info.get('redis_version', 'Unknown'),
                'uptime_in_days': info.get('uptime_in_days', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'evicted_keys': info.get('evicted_keys', 0),
                'expired_keys': info.get('expired_keys', 0),
            }
            
            # Calculate cache hit rate
            hits = stats['keyspace_hits']
            misses = stats['keyspace_misses']
            total_requests = hits + misses
            stats['hit_rate'] = (hits / total_requests * 100) if total_requests > 0 else 0.0
            stats['miss_rate'] = (misses / total_requests * 100) if total_requests > 0 else 0.0
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}", exc_info=True)
            return {
                'available': True,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Quick health check for monitoring systems
        Returns simple status for health endpoints
        """
        if not self._is_available():
            return {
                'status': 'unavailable',
                'message': 'Redis not connected'
            }
        
        try:
            # Ping Redis
            response_time_start = datetime.now()
            self.redis_client.ping()
            response_time = (datetime.now() - response_time_start).total_seconds() * 1000
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'message': 'Redis is responding'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }