"""
Tests for places_engine.cache module.
"""
import pytest
from unittest.mock import Mock, patch


class TestPlacesCache:
    """Test PlacesCache class."""
    
    def test_import_cache(self):
        """Test cache can be imported."""
        from places_engine.cache import PlacesCache
        assert PlacesCache is not None
    
    def test_create_cache_with_mock_client(self):
        """Test cache can be created with mock Redis client."""
        from places_engine.cache import PlacesCache
        mock_redis = Mock()
        cache = PlacesCache(redis_client=mock_redis)
        assert cache is not None
        assert cache._client is mock_redis
    
    def test_cache_key_generation_location(self):
        """Test location cache key generation."""
        from places_engine.cache import PlacesCache
        mock_redis = Mock()
        cache = PlacesCache(redis_client=mock_redis)
        key = cache.location_key('new york')
        assert 'location' in key
        assert 'new_york' in key
    
    def test_cache_key_generation_country(self):
        """Test country cache key generation."""
        from places_engine.cache import PlacesCache
        mock_redis = Mock()
        cache = PlacesCache(redis_client=mock_redis)
        key = cache.country_key('argentina')
        assert 'country' in key
        assert 'argentina' in key
    
    def test_cache_key_generation_nearby(self):
        """Test nearby cache key generation."""
        from places_engine.cache import PlacesCache
        mock_redis = Mock()
        cache = PlacesCache(redis_client=mock_redis)
        key = cache.nearby_key(40.7128, -74.0060, 10000)
        assert 'nearby' in key
    
    def test_normalize_query(self):
        """Test query normalization."""
        from places_engine.cache import PlacesCache
        mock_redis = Mock()
        cache = PlacesCache(redis_client=mock_redis)
        assert cache._normalize_query('New York City') == 'new_york_city'
        assert cache._normalize_query('  San  José  ') == 'san_jos'
        assert cache._normalize_query('') == ''


class TestPlacesCacheWithMockRedis:
    """Test PlacesCache with mocked Redis."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        return Mock()
    
    def test_get_location_with_redis(self, mock_redis):
        """Test get_location with Redis client."""
        from places_engine.cache import PlacesCache
        import json
        
        expected_data = {'places': [{'name': 'Test'}]}
        mock_redis.get.return_value = json.dumps(expected_data)
        
        cache = PlacesCache(redis_client=mock_redis)
        result = cache.get_location('test')
        
        assert result == expected_data
        mock_redis.get.assert_called_once()
    
    def test_set_location_with_redis(self, mock_redis):
        """Test set_location with Redis client."""
        from places_engine.cache import PlacesCache
        
        cache = PlacesCache(redis_client=mock_redis)
        result = cache.set_location('test', {'data': 'value'})
        
        # The implementation uses set with ex parameter
        mock_redis.set.assert_called_once()
        assert result is True
    
    def test_cache_miss_returns_none(self, mock_redis):
        """Test cache miss returns None."""
        from places_engine.cache import PlacesCache
        
        mock_redis.get.return_value = None
        
        cache = PlacesCache(redis_client=mock_redis)
        result = cache.get_location('nonexistent')
        
        assert result is None
