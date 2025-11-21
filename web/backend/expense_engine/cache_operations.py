"""
Expense Management System - Redis Cache Operations
High-performance caching for expense data
Handles 100+ concurrent users with optimized cache strategies
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import timedelta
import redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError
from .constants import CacheConfig, RedisConfig

logger = logging.getLogger(__name__)


class ExpenseCacheOperations:
    """Redis caching operations for expense management"""
    
    # Import TTL settings from constants
    TTL_USER = CacheConfig.TTL_USER
    TTL_GROUP = CacheConfig.TTL_GROUP
    TTL_EXPENSE = CacheConfig.TTL_EXPENSE
    TTL_BALANCE = CacheConfig.TTL_BALANCE
    TTL_INVITATION = CacheConfig.TTL_INVITATION
    
    # Import cache key prefixes from constants
    PREFIX_USER = CacheConfig.PREFIX_USER
    PREFIX_GROUP = CacheConfig.PREFIX_GROUP
    PREFIX_EXPENSE = CacheConfig.PREFIX_EXPENSE
    PREFIX_BALANCE = CacheConfig.PREFIX_BALANCE
    PREFIX_USER_GROUPS = CacheConfig.PREFIX_USER_GROUPS
    PREFIX_GROUP_EXPENSES = CacheConfig.PREFIX_GROUP_EXPENSES
    PREFIX_USER_EXPENSES = CacheConfig.PREFIX_USER_EXPENSES
    PREFIX_INVITATIONS = CacheConfig.PREFIX_INVITATIONS
    PREFIX_SETTLEMENTS = CacheConfig.PREFIX_SETTLEMENTS
    
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
            # Create explicit connection pool with optimized settings
            self.redis_pool = redis.ConnectionPool(
                host=RedisConfig.DEFAULT_HOST,
                port=RedisConfig.DEFAULT_PORT,
                max_connections=self.max_connections,
                socket_timeout=RedisConfig.SOCKET_TIMEOUT,
                socket_connect_timeout=RedisConfig.SOCKET_CONNECT_TIMEOUT,
                socket_keepalive=RedisConfig.SOCKET_KEEPALIVE,
                retry_on_timeout=RedisConfig.RETRY_ON_TIMEOUT,
                decode_responses=RedisConfig.DECODE_RESPONSES,
                health_check_interval=RedisConfig.HEALTH_CHECK_INTERVAL
            )
            
            # Create Redis client using the connection pool
            self.redis_client = redis.Redis(
                connection_pool=self.redis_pool
            )
            
            # Test connection
            self.redis_client.ping()
            
            logger.info("✅ Redis connection pool initialized successfully")
            logger.info(f"   Max connections: {self.max_connections}")
            logger.info(f"   Socket timeout: {RedisConfig.SOCKET_TIMEOUT}s")
            logger.info(f"   Connection pooling: ENABLED")
            
        except ConnectionError as e:
            logger.warning(f"⚠️  Redis connection failed: {e}")
            logger.warning("📝 To fix: Install and start Redis server")
            logger.warning("   Windows: Download from https://github.com/microsoftarchive/redis/releases")
            logger.warning("   Or use Docker: docker run -d -p 6379:6379 redis:alpine")
            logger.warning("   Or use WSL: sudo apt install redis-server && sudo service redis-server start")
            self.redis_client = None
            self.redis_pool = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis cache: {e}")
            self.redis_client = None
            self.redis_pool = None
    
    def _is_available(self) -> bool:
        """Check if Redis is available"""
        if self.redis_client is None:
            return False
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False
    
    # =========================================================================
    # USER CACHE
    # =========================================================================
    
    def cache_user(self, user_id: str, user_data: Dict) -> bool:
        """Cache user data"""
        if not self._is_available():
            return False
        try:
            key = f"{self.PREFIX_USER}{user_id}"
            self.redis_client.setex(key, self.TTL_USER, json.dumps(user_data))
            
            # Also cache by username and email for quick lookups
            if 'username' in user_data:
                username_key = f"{self.PREFIX_USER}username:{user_data['username']}"
                self.redis_client.setex(username_key, self.TTL_USER, user_id)
            
            if 'email' in user_data:
                email_key = f"{self.PREFIX_USER}email:{user_data['email']}"
                self.redis_client.setex(email_key, self.TTL_USER, user_id)
            
            return True
        except RedisError as e:
            logger.error(f"Error caching user: {e}")
            return False
    
    def get_cached_user(self, user_id: str) -> Optional[Dict]:
        """Get cached user data"""
        if not self._is_available():
            return None
        try:
            key = f"{self.PREFIX_USER}{user_id}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cached user: {e}")
            return None
    
    def get_user_by_username_cached(self, username: str) -> Optional[str]:
        """Get user ID by username from cache"""
        if not self._is_available():
            return None
        try:
            key = f"{self.PREFIX_USER}username:{username}"
            return self.redis_client.get(key)
        except RedisError as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    def get_user_by_email_cached(self, email: str) -> Optional[str]:
        """Get user ID by email from cache"""
        if not self._is_available():
            return None
        try:
            key = f"{self.PREFIX_USER}email:{email}"
            return self.redis_client.get(key)
        except RedisError as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def invalidate_user(self, user_id: str, username: Optional[str] = None, 
                       email: Optional[str] = None):
        """Invalidate user cache"""
        if not self._is_available():
            return
        try:
            keys = [f"{self.PREFIX_USER}{user_id}"]
            if username:
                keys.append(f"{self.PREFIX_USER}username:{username}")
            if email:
                keys.append(f"{self.PREFIX_USER}email:{email}")
            
            self.redis_client.delete(*keys)
        except RedisError as e:
            logger.error(f"Error invalidating user cache: {e}")
    
    # =========================================================================
    # GROUP CACHE
    # =========================================================================
    
    def cache_group(self, group_id: str, group_data: Dict) -> bool:
        """Cache group data"""
        if not self._is_available():
            return False
        try:
            key = f"{self.PREFIX_GROUP}{group_id}"
            self.redis_client.setex(key, self.TTL_GROUP, json.dumps(group_data))
            return True
        except RedisError as e:
            logger.error(f"Error caching group: {e}")
            return False
    
    def get_cached_group(self, group_id: str) -> Optional[Dict]:
        """Get cached group data"""
        if not self._is_available():
            return None
        try:
            key = f"{self.PREFIX_GROUP}{group_id}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cached group: {e}")
            return None
    
    def cache_user_groups(self, user_id: str, groups: List[Dict]) -> bool:
        """Cache user's groups list"""
        if not self._is_available():
            return False
        try:
            key = f"{self.PREFIX_USER_GROUPS}{user_id}"
            self.redis_client.setex(key, self.TTL_GROUP, json.dumps(groups))
            return True
        except RedisError as e:
            logger.error(f"Error caching user groups: {e}")
            return False
    
    def get_cached_user_groups(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached user groups"""
        if not self._is_available():
            return None
        try:
            key = f"{self.PREFIX_USER_GROUPS}{user_id}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cached user groups: {e}")
            return None
    
    def invalidate_group(self, group_id: str):
        """Invalidate group cache and related caches"""
        if not self._is_available():
            return
        try:
            keys = [
                f"{self.PREFIX_GROUP}{group_id}",
                f"{self.PREFIX_GROUP_EXPENSES}{group_id}",
                f"{self.PREFIX_SETTLEMENTS}{group_id}"
            ]
            self.redis_client.delete(*keys)
            
            # Also invalidate user groups cache for all members
            # This is simplified - in production, you'd track memberships
        except RedisError as e:
            logger.error(f"Error invalidating group cache: {e}")
    
    def invalidate_user_groups(self, user_id: str):
        """Invalidate user's groups cache (both full and summary modes)
        
        🔥 CRITICAL FIX: Deletes BOTH cache variants:
        - user_groups:USER123 (full mode)
        - user_groups:USER123_summary (summary mode)
        
        This fixes the bug where deleted groups still appear because
        summary cache wasn't being invalidated.
        
        NOTE: Uses PREFIX_USER_GROUPS_KEY (not PREFIX_USER_GROUPS) to match
        the key format used by service.py get_user_groups()
        """
        if not self._is_available():
            return
        try:
            # ✅ CRITICAL: Use CacheConfig.PREFIX_USER_GROUPS_KEY to match service.py
            base_key = f"{CacheConfig.PREFIX_USER_GROUPS_KEY}{user_id}"
            summary_key = f"{CacheConfig.PREFIX_USER_GROUPS_KEY}{user_id}_summary"
            self.redis_client.delete(base_key, summary_key)
            logger.info(f"🔄 Invalidated user groups cache for {user_id}: {base_key} + {summary_key}")
        except RedisError as e:
            logger.error(f"Error invalidating user groups cache: {e}")
    
    # =========================================================================
    # EXPENSE CACHE
    # =========================================================================
    
    def cache_expense(self, expense_id: str, expense_data: Dict) -> bool:
        """Cache expense data"""
        if not self._is_available():
            return False
        try:
            key = f"{self.PREFIX_EXPENSE}{expense_id}"
            self.redis_client.setex(key, self.TTL_EXPENSE, json.dumps(expense_data))
            return True
        except RedisError as e:
            logger.error(f"Error caching expense: {e}")
            return False
    
    def get_cached_expense(self, expense_id: str) -> Optional[Dict]:
        """Get cached expense data"""
        if not self._is_available():
            return None
        try:
            key = f"{self.PREFIX_EXPENSE}{expense_id}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cached expense: {e}")
            return None
    
    def cache_group_expenses(self, group_id: str, expenses: List[Dict]) -> bool:
        """Cache group expenses list"""
        if not self._is_available():
            return False
        try:
            key = f"{self.PREFIX_GROUP_EXPENSES}{group_id}"
            self.redis_client.setex(key, self.TTL_EXPENSE, json.dumps(expenses))
            return True
        except RedisError as e:
            logger.error(f"Error caching group expenses: {e}")
            return False
    
    def get_cached_group_expenses(self, group_id: str) -> Optional[List[Dict]]:
        """Get cached group expenses"""
        if not self._is_available():
            return None
        try:
            key = f"{self.PREFIX_GROUP_EXPENSES}{group_id}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cached group expenses: {e}")
            return None
    
    def cache_user_expenses(self, user_id: str, group_id: Optional[str], 
                           expenses: List[Dict]) -> bool:
        """Cache user expenses"""
        if not self._is_available():
            return False
        try:
            cache_key = f"{group_id}" if group_id else "personal"
            key = f"{self.PREFIX_USER_EXPENSES}{user_id}:{cache_key}"
            self.redis_client.setex(key, self.TTL_EXPENSE, json.dumps(expenses))
            return True
        except RedisError as e:
            logger.error(f"Error caching user expenses: {e}")
            return False
    
    def get_cached_user_expenses(self, user_id: str, 
                                group_id: Optional[str]) -> Optional[List[Dict]]:
        """Get cached user expenses"""
        if not self._is_available():
            return None
        try:
            cache_key = f"{group_id}" if group_id else "personal"
            key = f"{self.PREFIX_USER_EXPENSES}{user_id}:{cache_key}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cached user expenses: {e}")
            return None
    
    def invalidate_expense(self, expense_id: str, group_id: Optional[str] = None):
        """Invalidate expense cache and related caches"""
        if not self._is_available():
            return
        try:
            keys = [f"{self.PREFIX_EXPENSE}{expense_id}"]
            
            if group_id:
                keys.append(f"{self.PREFIX_GROUP_EXPENSES}{group_id}")
            
            self.redis_client.delete(*keys)
        except RedisError as e:
            logger.error(f"Error invalidating expense cache: {e}")
    
    def invalidate_user_expenses(self, user_id: str, group_id: Optional[str] = None):
        """Invalidate user expenses cache"""
        if not self._is_available():
            return
        try:
            cache_key = f"{group_id}" if group_id else "personal"
            key = f"{self.PREFIX_USER_EXPENSES}{user_id}:{cache_key}"
            self.redis_client.delete(key)
        except RedisError as e:
            logger.error(f"Error invalidating user expenses cache: {e}")
    
    # =========================================================================
    # BALANCE CACHE
    # =========================================================================
    
    def cache_balance(self, user_id: str, group_id: Optional[str], 
                     balance_data: Dict) -> bool:
        """Cache balance data"""
        if not self._is_available():
            return False
        try:
            cache_key = f"{group_id}" if group_id else "overall"
            key = f"{self.PREFIX_BALANCE}{user_id}:{cache_key}"
            self.redis_client.setex(key, self.TTL_BALANCE, json.dumps(balance_data))
            return True
        except RedisError as e:
            logger.error(f"Error caching balance: {e}")
            return False
    
    def get_cached_balance(self, user_id: str, 
                          group_id: Optional[str]) -> Optional[Dict]:
        """Get cached balance"""
        if not self._is_available():
            return None
        try:
            cache_key = f"{group_id}" if group_id else "overall"
            key = f"{self.PREFIX_BALANCE}{user_id}:{cache_key}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cached balance: {e}")
            return None
    
    def invalidate_balance(self, user_id: str, group_id: Optional[str] = None):
        """Invalidate balance cache"""
        if not self._is_available():
            return
        try:
            if group_id:
                key = f"{self.PREFIX_BALANCE}{user_id}:{group_id}"
                self.redis_client.delete(key)
            else:
                # Invalidate all balances for user
                pattern = f"{self.PREFIX_BALANCE}{user_id}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
        except RedisError as e:
            logger.error(f"Error invalidating balance cache: {e}")
    
    def invalidate_group_balances(self, group_id: str, user_ids: List[str]):
        """Invalidate all balances for a group"""
        if not self._is_available():
            return
        try:
            keys = [f"{self.PREFIX_BALANCE}{uid}:{group_id}" for uid in user_ids]
            if keys:
                self.redis_client.delete(*keys)
        except RedisError as e:
            logger.error(f"Error invalidating group balances: {e}")
    
    # =========================================================================
    # INVITATION CACHE
    # =========================================================================
    
    def cache_user_invitations(self, user_id: str, invitations: List[Dict]) -> bool:
        """Cache user invitations"""
        if not self._is_available():
            return False
        try:
            key = f"{self.PREFIX_INVITATIONS}{user_id}"
            self.redis_client.setex(key, self.TTL_INVITATION, json.dumps(invitations))
            return True
        except RedisError as e:
            logger.error(f"Error caching invitations: {e}")
            return False
    
    def get_cached_user_invitations(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached user invitations"""
        if not self._is_available():
            return None
        try:
            key = f"{self.PREFIX_INVITATIONS}{user_id}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cached invitations: {e}")
            return None
    
    def invalidate_user_invitations(self, user_id: str):
        """Invalidate user invitations cache"""
        if not self._is_available():
            return
        try:
            key = f"{self.PREFIX_INVITATIONS}{user_id}"
            self.redis_client.delete(key)
        except RedisError as e:
            logger.error(f"Error invalidating invitations cache: {e}")
    
    # =========================================================================
    # SETTLEMENT CACHE
    # =========================================================================
    
    def cache_group_settlements(self, group_id: str, settlements: List[Dict]) -> bool:
        """Cache group settlements"""
        if not self._is_available():
            return False
        try:
            key = f"{self.PREFIX_SETTLEMENTS}{group_id}"
            self.redis_client.setex(key, self.TTL_EXPENSE, json.dumps(settlements))
            return True
        except RedisError as e:
            logger.error(f"Error caching settlements: {e}")
            return False
    
    def get_cached_group_settlements(self, group_id: str) -> Optional[List[Dict]]:
        """Get cached group settlements"""
        if not self._is_available():
            return None
        try:
            key = f"{self.PREFIX_SETTLEMENTS}{group_id}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cached settlements: {e}")
            return None
    
    def invalidate_settlements(self, group_id: str):
        """Invalidate settlements cache"""
        if not self._is_available():
            return
        try:
            key = f"{self.PREFIX_SETTLEMENTS}{group_id}"
            self.redis_client.delete(key)
        except RedisError as e:
            logger.error(f"Error invalidating settlements cache: {e}")
    
    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================
    
    def invalidate_all_for_user(self, user_id: str):
        """Invalidate all caches for a user"""
        if not self._is_available():
            return
        try:
            patterns = [
                f"{self.PREFIX_USER}{user_id}*",
                f"{self.PREFIX_BALANCE}{user_id}:*",
                f"{self.PREFIX_USER_EXPENSES}{user_id}:*",
                f"{self.PREFIX_USER_GROUPS}{user_id}",
                f"{self.PREFIX_INVITATIONS}{user_id}"
            ]
            
            for pattern in patterns:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
        except RedisError as e:
            logger.error(f"Error invalidating all user caches: {e}")
    
    def invalidate_all_for_group(self, group_id: str, member_ids: List[str]):
        """Invalidate all caches related to a group"""
        if not self._is_available():
            return
        try:
            # Invalidate group data
            self.invalidate_group(group_id)
            
            # Invalidate balances for all members
            self.invalidate_group_balances(group_id, member_ids)
            
            # Invalidate user groups cache for all members
            for user_id in member_ids:
                self.invalidate_user_groups(user_id)
                self.invalidate_user_expenses(user_id, group_id)
        except RedisError as e:
            logger.error(f"Error invalidating all group caches: {e}")
    
    def clear_all_expense_cache(self):
        """Clear all expense-related cache (use with caution)"""
        if not self._is_available():
            return
        try:
            pattern = "expense:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} expense cache keys")
        except RedisError as e:
            logger.error(f"Error clearing expense cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._is_available():
            return {'status': 'unavailable'}
        try:
            info = self.redis_client.info()
            stats = {
                'status': 'healthy',
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'N/A'),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
            }
            
            # Calculate hit rate
            hits = stats['keyspace_hits']
            misses = stats['keyspace_misses']
            total = hits + misses
            if total > 0:
                stats['hit_rate'] = round((hits / total) * 100, 2)
            else:
                stats['hit_rate'] = 0
            
            return stats
        except RedisError as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'status': 'error', 'error': str(e)}
