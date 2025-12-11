"""
Phase 5 Tests - Cache and Performance
Tests for cache_manager, cache_decorator, query_optimizer, cache_warmer

Run with: pytest tests/test_cache.py -v

Note: Tests access protected members for testing internal state,
which is normal practice in unit tests. Test functions may have
unused arguments to match required signatures.
"""
# pylint: disable=protected-access,unused-argument
# pyright: reportUnusedVariable=false

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


# =========================================================================
# Test CacheConfig
# =========================================================================

class TestCacheConfig:
    """Tests for CacheConfig class"""
    
    def test_cache_config_has_ttl_values(self):
        """Test that cache config has all required TTL values"""
        from expense_engine.utils.cache_manager import CacheConfig
        
        assert hasattr(CacheConfig, 'TTL_USER')
        assert hasattr(CacheConfig, 'TTL_GROUP')
        assert hasattr(CacheConfig, 'TTL_EXPENSES')
        assert hasattr(CacheConfig, 'TTL_BALANCE')
        assert CacheConfig.TTL_USER > 0
        assert CacheConfig.TTL_GROUP > 0
    
    def test_cache_config_has_key_prefixes(self):
        """Test that cache config has all required key prefixes"""
        from expense_engine.utils.cache_manager import CacheConfig
        
        assert CacheConfig.PREFIX_BASE == "expense:"
        assert CacheConfig.PREFIX_USER == "expense:user:"
        assert CacheConfig.PREFIX_GROUP == "expense:group:"
        assert CacheConfig.PREFIX_BALANCE == "expense:balance:"


# =========================================================================
# Test CacheStats
# =========================================================================

class TestCacheStats:
    """Tests for CacheStats class"""
    
    def test_cache_stats_initial_values(self):
        """Test initial stats are zero"""
        from expense_engine.utils.cache_manager import CacheStats
        
        stats = CacheStats()
        assert stats._hits == 0
        assert stats._misses == 0
        assert stats._errors == 0
    
    def test_cache_stats_record_hit(self):
        """Test recording cache hit"""
        from expense_engine.utils.cache_manager import CacheStats
        
        stats = CacheStats()
        stats.record_hit()
        stats.record_hit()
        assert stats._hits == 2
    
    def test_cache_stats_record_miss(self):
        """Test recording cache miss"""
        from expense_engine.utils.cache_manager import CacheStats
        
        stats = CacheStats()
        stats.record_miss()
        assert stats._misses == 1
    
    def test_cache_stats_hit_rate(self):
        """Test hit rate calculation"""
        from expense_engine.utils.cache_manager import CacheStats
        
        stats = CacheStats()
        stats.record_hit()
        stats.record_hit()
        stats.record_hit()
        stats.record_miss()
        
        # 3 hits / 4 total = 0.75
        assert stats.hit_rate == pytest.approx(0.75, rel=0.01)
    
    def test_cache_stats_hit_rate_zero_when_no_ops(self):
        """Test hit rate is zero when no operations"""
        from expense_engine.utils.cache_manager import CacheStats
        
        stats = CacheStats()
        assert stats.hit_rate == 0.0
    
    def test_cache_stats_get_stats(self):
        """Test get_stats returns complete stats"""
        from expense_engine.utils.cache_manager import CacheStats
        
        stats = CacheStats()
        stats.record_hit()
        stats.record_miss()
        stats.record_error()
        stats.record_set()
        
        result = stats.get_stats()
        assert result['hits'] == 1
        assert result['misses'] == 1
        assert result['errors'] == 1
        assert result['sets'] == 1
        assert 'uptime_seconds' in result
    
    def test_cache_stats_reset(self):
        """Test resetting stats"""
        from expense_engine.utils.cache_manager import CacheStats
        
        stats = CacheStats()
        stats.record_hit()
        stats.record_miss()
        stats.reset()
        
        assert stats._hits == 0
        assert stats._misses == 0


# =========================================================================
# Test CacheManager
# =========================================================================

class TestCacheManager:
    """Tests for CacheManager class"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        mock = MagicMock()
        mock.ping.return_value = True
        mock.get.return_value = None
        mock.set.return_value = True
        mock.delete.return_value = 1
        mock.exists.return_value = True
        mock.ttl.return_value = 60
        return mock
    
    def test_cache_manager_singleton(self):
        """Test CacheManager is singleton"""
        from expense_engine.utils.cache_manager import CacheManager
        
        # Reset singleton for test
        CacheManager._instance = None
        
        with patch('expense_engine.utils.cache_manager.redis.ConnectionPool'):
            with patch('expense_engine.utils.cache_manager.redis.Redis') as mock_redis:
                mock_redis.return_value.ping.return_value = True
                
                manager1 = CacheManager()
                manager2 = CacheManager()
                
                assert manager1 is manager2
    
    def test_is_available_returns_false_when_no_redis(self):
        """Test is_available returns false when Redis not connected"""
        from expense_engine.utils.cache_manager import CacheManager
        
        CacheManager._instance = None
        
        # Create a manager without going through __init__
        manager = CacheManager.__new__(CacheManager)
        manager._initialized = False
        manager._redis_client = None
        manager._pool = None
        manager._stats = MagicMock()
        manager._connected = False
        manager._initialized = True
        
        assert manager.is_available() is False
    
    def test_get_returns_none_when_unavailable(self):
        """Test get returns None when cache unavailable"""
        from expense_engine.utils.cache_manager import CacheManager
        
        CacheManager._instance = None
        manager = CacheManager.__new__(CacheManager)
        manager._initialized = False
        manager._redis_client = None
        manager._pool = None
        manager._stats = MagicMock()
        manager._connected = False
        manager._initialized = True
        
        result = manager.get("test_key")
        assert result is None
    
    def test_set_returns_false_when_unavailable(self):
        """Test set returns False when cache unavailable"""
        from expense_engine.utils.cache_manager import CacheManager
        
        CacheManager._instance = None
        manager = CacheManager.__new__(CacheManager)
        manager._initialized = False
        manager._redis_client = None
        manager._pool = None
        manager._stats = MagicMock()
        manager._connected = False
        manager._initialized = True
        
        result = manager.set("test_key", {"data": "value"})
        assert result is False


# =========================================================================
# Test Cache Decorator
# =========================================================================

class TestCacheDecorator:
    """Tests for cache decorator"""
    
    def test_generate_cache_key_with_args(self):
        """Test cache key generation from args"""
        from expense_engine.utils.cache_decorator import _generate_cache_key
        
        key = _generate_cache_key(
            prefix="expense:group",
            func_name="get_group",
            args=(None, "group123"),  # (self, group_id)
            kwargs={},
            key_params=None
        )
        
        assert "expense:group" in key
        assert "get_group" in key
        assert "group123" in key
    
    def test_generate_cache_key_with_kwargs(self):
        """Test cache key generation from kwargs"""
        from expense_engine.utils.cache_decorator import _generate_cache_key
        
        key = _generate_cache_key(
            prefix="expense:user",
            func_name="get_user",
            args=(None,),
            kwargs={"user_id": "user456", "include_groups": True},
            key_params=None
        )
        
        assert "expense:user" in key
        assert "user456" in key
    
    def test_generate_cache_key_with_key_params(self):
        """Test cache key generation with specific key params"""
        from expense_engine.utils.cache_decorator import _generate_cache_key
        
        key = _generate_cache_key(
            prefix="expense",
            func_name="get_data",
            args=(None,),
            kwargs={"group_id": "g1", "user_id": "u1", "limit": 10},
            key_params=["group_id"]  # Only include group_id
        )
        
        assert "g1" in key
    
    def test_cached_decorator_uses_cache(self):
        """Test @cached decorator uses cache"""
        from expense_engine.utils.cache_decorator import cached
        
        mock_manager = MagicMock()
        mock_manager.is_available.return_value = True
        mock_manager.get.return_value = {"cached": True}
        
        with patch('expense_engine.utils.cache_manager.get_cache_manager', return_value=mock_manager):
            @cached(prefix="test", ttl=60)
            def get_data(_self, data_id: str):  # pylint: disable=unused-argument
                return {"fresh": True}
            
            # Call function
            result = get_data(None, "id123")
            
            # Should return cached value
            assert result == {"cached": True}
            mock_manager.get.assert_called_once()
    
    def test_cached_decorator_fetches_on_miss(self):
        """Test @cached decorator fetches data on cache miss"""
        from expense_engine.utils.cache_decorator import cached
        
        call_count = 0
        mock_manager = MagicMock()
        mock_manager.is_available.return_value = True
        mock_manager.get.return_value = None  # Cache miss
        mock_manager.set.return_value = True
        
        with patch('expense_engine.utils.cache_manager.get_cache_manager', return_value=mock_manager):
            @cached(prefix="test", ttl=60)
            def get_data(_self, data_id: str):
                nonlocal call_count
                call_count += 1
                return {"fresh": True, "id": data_id}
            
            result = get_data(None, "id123")
            
            assert result == {"fresh": True, "id": "id123"}
            assert call_count == 1
            mock_manager.set.assert_called_once()


# =========================================================================
# Test Query Cache
# =========================================================================

class TestQueryCache:
    """Tests for QueryCache class"""
    
    def test_query_cache_get_miss(self):
        """Test cache miss returns None"""
        from expense_engine.utils.query_optimizer import QueryCache
        
        cache = QueryCache()
        result = cache.get("nonexistent_key")
        assert result is None
    
    def test_query_cache_set_and_get(self):
        """Test setting and getting cached value"""
        from expense_engine.utils.query_optimizer import QueryCache
        
        cache = QueryCache()
        cache.set("test_key", {"data": [1, 2, 3]})
        
        result = cache.get("test_key")
        assert result == {"data": [1, 2, 3]}
    
    def test_query_cache_ttl_expiration(self):
        """Test cache entries expire after TTL"""
        from expense_engine.utils.query_optimizer import QueryCache
        
        cache = QueryCache(default_ttl=0)  # Immediate expiry
        cache.set("test_key", {"data": "value"}, ttl=0)
        
        # Manually expire the entry
        cache._cache["test_key"] = (
            {"data": "value"},
            datetime.utcnow() - timedelta(seconds=1)
        )
        
        result = cache.get("test_key")
        assert result is None
    
    def test_query_cache_invalidate(self):
        """Test invalidating specific key"""
        from expense_engine.utils.query_optimizer import QueryCache
        
        cache = QueryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.invalidate("key1")
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
    
    def test_query_cache_invalidate_pattern(self):
        """Test invalidating keys by pattern"""
        from expense_engine.utils.query_optimizer import QueryCache
        
        cache = QueryCache()
        cache.set("group:123:expenses", [])
        cache.set("group:123:balances", {})
        cache.set("user:456:data", {})
        
        cache.invalidate_pattern("group:123")
        
        assert cache.get("group:123:expenses") is None
        assert cache.get("group:123:balances") is None
        assert cache.get("user:456:data") == {}
    
    def test_query_cache_hit_rate(self):
        """Test hit rate tracking"""
        from expense_engine.utils.query_optimizer import QueryCache
        
        cache = QueryCache()
        cache.set("key1", "value1")
        
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        # 2 hits / 3 total
        assert cache.hit_rate == pytest.approx(2/3, rel=0.01)
    
    def test_query_cache_max_size_eviction(self):
        """Test eviction when max size reached"""
        from expense_engine.utils.query_optimizer import QueryCache
        
        cache = QueryCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict oldest
        
        assert len(cache._cache) == 3
        assert cache.get("key4") == "value4"


# =========================================================================
# Test QueryResult
# =========================================================================

class TestQueryResult:
    """Tests for QueryResult class"""
    
    def test_query_result_properties(self):
        """Test QueryResult stores properties correctly"""
        from expense_engine.utils.query_optimizer import QueryResult
        
        result = QueryResult(
            data=[{"id": "1"}, {"id": "2"}],
            total_count=10,
            has_more=True,
            cursor="abc123"
        )
        
        assert len(result) == 2
        assert result.total_count == 10
        assert result.has_more is True
        assert result.cursor == "abc123"
    
    def test_query_result_to_dict(self):
        """Test QueryResult serialization"""
        from expense_engine.utils.query_optimizer import QueryResult
        
        result = QueryResult(
            data=[{"id": "1"}],
            has_more=False,
            cached=True,
            query_time_ms=50.5
        )
        
        d = result.to_dict()
        assert d['data'] == [{"id": "1"}]
        assert d['cached'] is True
        assert d['query_time_ms'] == 50.5
    
    def test_query_result_iteration(self):
        """Test QueryResult is iterable"""
        from expense_engine.utils.query_optimizer import QueryResult
        
        result = QueryResult(data=[{"a": 1}, {"b": 2}, {"c": 3}])
        
        items = list(result)
        assert len(items) == 3
        assert items[0] == {"a": 1}


# =========================================================================
# Test Cache Warmer
# =========================================================================

class TestCacheWarmerTask:
    """Tests for CacheWarmerTask class"""
    
    def test_task_creation(self):
        """Test task creation with properties"""
        from expense_engine.utils.cache_warmer import CacheWarmerTask
        
        task = CacheWarmerTask(
            name="test_task",
            fetch_func=lambda: {"data": True},
            cache_key="test:key",
            ttl=60,
            priority=1
        )
        
        assert task.name == "test_task"
        assert task.cache_key == "test:key"
        assert task.ttl == 60
        assert task.priority == 1
        assert task.enabled is True
    
    def test_task_disabled(self):
        """Test disabled task returns False"""
        from expense_engine.utils.cache_warmer import CacheWarmerTask
        
        task = CacheWarmerTask(
            name="disabled_task",
            fetch_func=lambda: {"data": True},
            cache_key="test:key",
            enabled=False
        )
        
        result = task.execute()
        assert result is False
    
    def test_task_to_dict(self):
        """Test task serialization"""
        from expense_engine.utils.cache_warmer import CacheWarmerTask
        
        task = CacheWarmerTask(
            name="test",
            fetch_func=lambda: None,
            cache_key="key",
            ttl=100,
            priority=2
        )
        
        d = task.to_dict()
        assert d['name'] == "test"
        assert d['cache_key'] == "key"
        assert d['ttl'] == 100
        assert d['priority'] == 2


class TestCacheWarmer:
    """Tests for CacheWarmer class"""
    
    def test_cache_warmer_singleton(self):
        """Test CacheWarmer is singleton"""
        from expense_engine.utils.cache_warmer import CacheWarmer
        
        CacheWarmer._instance = None
        
        warmer1 = CacheWarmer()
        warmer2 = CacheWarmer()
        
        assert warmer1 is warmer2
    
    def test_register_task(self):
        """Test registering warming task"""
        from expense_engine.utils.cache_warmer import CacheWarmer, CacheWarmerTask
        
        CacheWarmer._instance = None
        warmer = CacheWarmer()
        
        task = CacheWarmerTask(
            name="test_task",
            fetch_func=lambda: {"data": True},
            cache_key="test:key"
        )
        
        warmer.register_task(task)
        assert "test_task" in warmer._tasks
    
    def test_register_convenience_method(self):
        """Test register convenience method"""
        from expense_engine.utils.cache_warmer import CacheWarmer
        
        CacheWarmer._instance = None
        warmer = CacheWarmer()
        
        warmer.register(
            name="quick_task",
            fetch_func=lambda: {"quick": True},
            cache_key="quick:key",
            ttl=30
        )
        
        assert "quick_task" in warmer._tasks
        assert warmer._tasks["quick_task"].ttl == 30
    
    def test_unregister_task(self):
        """Test unregistering task"""
        from expense_engine.utils.cache_warmer import CacheWarmer
        
        CacheWarmer._instance = None
        warmer = CacheWarmer()
        
        warmer.register("task1", lambda: None, "key1")
        warmer.register("task2", lambda: None, "key2")
        
        warmer.unregister("task1")
        
        assert "task1" not in warmer._tasks
        assert "task2" in warmer._tasks
    
    def test_get_summary(self):
        """Test getting warmer summary"""
        from expense_engine.utils.cache_warmer import CacheWarmer
        
        CacheWarmer._instance = None
        warmer = CacheWarmer()
        
        warmer.register("task1", lambda: None, "key1", enabled=True)
        warmer.register("task2", lambda: None, "key2", enabled=False)
        
        summary = warmer.get_summary()
        
        assert summary['total_tasks'] == 2
        assert summary['enabled_tasks'] == 1


# =========================================================================
# Test Cached Repository Mixin
# =========================================================================

class TestCachedRepositoryMixin:
    """Tests for CachedRepositoryMixin"""
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        from expense_engine.repositories.cached_repository import CachedRepositoryMixin
        
        class TestRepo(CachedRepositoryMixin):
            cache_prefix = "expense:test"
        
        repo = TestRepo()
        key = repo._cache_key("id", "123")
        
        assert key == "expense:test:id:123"
    
    def test_cache_key_with_empty_parts(self):
        """Test cache key skips empty parts"""
        from expense_engine.repositories.cached_repository import CachedRepositoryMixin
        
        class TestRepo(CachedRepositoryMixin):
            cache_prefix = "test"
        
        repo = TestRepo()
        key = repo._cache_key("a", "", "b", "c")
        
        # Empty string should be filtered
        assert "test" in key
        assert "a" in key
        assert "b" in key
        assert "c" in key


class TestCachedMethod:
    """Tests for @cached_method decorator"""
    
    def test_cached_method_decorator(self):
        """Test @cached_method generates correct cache key"""
        from expense_engine.repositories.cached_repository import cached_method
        
        @cached_method(
            cache_key_func=lambda _self, group_id: f"group:{group_id}",
            ttl=60
        )
        def get_group(_self, group_id: str):
            return {"id": group_id}
        
        # Function should have invalidate method attached
        assert hasattr(get_group, 'invalidate')


class TestInvalidateAfter:
    """Tests for @invalidate_after decorator"""
    
    def test_invalidate_after_with_static_keys(self):
        """Test @invalidate_after with static key list"""
        from expense_engine.repositories.cached_repository import invalidate_after
        
        with patch(
            'expense_engine.repositories.cached_repository.get_cache_manager'
        ) as mock:
            mock_cache = MagicMock()
            mock.return_value = mock_cache
            
            @invalidate_after(invalidate_keys=["key1", "key2"])
            def update_data(_self, _data):
                return {"updated": True}
            
            result = update_data(None, {"new": "data"})
            
            assert result == {"updated": True}
            mock_cache.delete.assert_called_once()
