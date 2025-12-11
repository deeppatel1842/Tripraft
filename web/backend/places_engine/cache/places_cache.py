"""
Places Engine Cache Module

Redis-based caching for places operations with configurable TTLs
and intelligent cache key generation.

Cache Strategy:
- Location search (city/state): 4 hours
- Country overview: 24 hours
- Nearby search: 1 hour
- Place detail: 24 hours
- Autocomplete: 1 hour
- Popular places: 1 hour
"""

import json
import hashlib
import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class FirestoreJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Firestore DatetimeWithNanoseconds."""
    def default(self, obj):
        # Handle Firestore DatetimeWithNanoseconds
        if hasattr(obj, 'timestamp'):
            # Convert to ISO format string
            return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class PlacesCache:
    """
    Redis cache manager for places API.
    
    Provides type-specific cache operations with configurable TTLs
    and automatic key generation.
    """
    
    # Cache TTLs in seconds
    TTL_LOCATION_SEARCH = 14400   # 4 hours
    TTL_COUNTRY_OVERVIEW = 86400  # 24 hours
    TTL_NEARBY_SEARCH = 3600      # 1 hour
    TTL_PLACE_DETAIL = 86400      # 24 hours
    TTL_AUTOCOMPLETE = 3600       # 1 hour
    TTL_POPULAR = 3600            # 1 hour
    TTL_CITY_LIST = 21600         # 6 hours
    
    PREFIX = "places"
    
    def __init__(self, redis_client: Optional[Any] = None):
        """
        Initialize PlacesCache.
        
        Args:
            redis_client: Redis client instance. If None, will be lazy loaded.
        """
        self._client = redis_client
    
    @property
    def client(self) -> Optional[Any]:
        """Get Redis client with lazy initialization."""
        if self._client is None:
            try:
                from cache.redis_client import redis_client
                self._client = redis_client.get_client()
            except ImportError:
                logger.warning("Redis client not available")
                return None
        return self._client
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query string for cache key."""
        if not query:
            return ""
        # Lowercase, remove special chars, collapse whitespace
        normalized = re.sub(r'[^a-z0-9\s]', '', query.lower())
        return '_'.join(normalized.split())
    
    def _build_key(self, *parts) -> str:
        """Build cache key from parts."""
        clean_parts = [str(p) for p in parts if p is not None]
        return f"{self.PREFIX}:{':'.join(clean_parts)}"
    
    def _hash_params(self, **params) -> str:
        """Create hash from parameters for complex cache keys."""
        sorted_params = sorted(
            (k, v) for k, v in params.items()
            if v is not None
        )
        param_str = json.dumps(sorted_params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:12]
    
    # ========== KEY GENERATORS ==========
    
    def location_key(self, query: str) -> str:
        """Generate key for location search (city/state)."""
        normalized = self._normalize_query(query)
        return self._build_key("location", normalized)
    
    def country_key(self, country: str) -> str:
        """Generate key for country overview."""
        normalized = self._normalize_query(country)
        return self._build_key("country", normalized)
    
    def nearby_key(self, lat: float, lng: float, radius: int) -> str:
        """Generate key for nearby search."""
        # Round to 4 decimal places (~11m precision)
        lat_round = round(lat, 4)
        lng_round = round(lng, 4)
        return self._build_key("nearby", f"{lat_round}", f"{lng_round}", f"{radius}")
    
    def place_key(self, place_id: str) -> str:
        """Generate key for place detail."""
        return self._build_key("detail", place_id)
    
    def autocomplete_key(self, query: str) -> str:
        """Generate key for autocomplete."""
        normalized = self._normalize_query(query)
        return self._build_key("autocomplete", normalized)
    
    def popular_key(self, country: Optional[str] = None, limit: int = 20) -> str:
        """Generate key for popular places."""
        if country:
            normalized = self._normalize_query(country)
            return self._build_key("popular", normalized, limit)
        return self._build_key("popular", "global", limit)
    
    def city_list_key(self, country: str) -> str:
        """Generate key for cities list."""
        normalized = self._normalize_query(country)
        return self._build_key("cities", normalized)
    
    def search_key(self, **params) -> str:
        """Generate key for general search."""
        param_hash = self._hash_params(**params)
        return self._build_key("search", param_hash)
    
    # ========== CORE OPERATIONS ==========
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached data by key."""
        if not self.client:
            return None
        
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
        return None
    
    def set(self, key: str, data: Dict, ttl: int) -> bool:
        """Set cached data with TTL."""
        if not self.client:
            return False
        
        try:
            # Use custom encoder to handle Firestore timestamps
            self.client.set(key, json.dumps(data, cls=FirestoreJSONEncoder), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
        return False
    
    def delete(self, key: str) -> bool:
        """Delete cached data by key."""
        if not self.client:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
        return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        if not self.client:
            return 0
        
        try:
            full_pattern = f"{self.PREFIX}:{pattern}"
            keys = self.client.keys(full_pattern)
            if keys:
                return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Cache invalidate error for {pattern}: {e}")
        return 0
    
    # ========== CONVENIENCE METHODS ==========
    
    def get_location(self, query: str) -> Optional[Dict]:
        """Get cached location search result."""
        return self.get(self.location_key(query))
    
    def set_location(self, query: str, data: Dict) -> bool:
        """Cache location search result."""
        return self.set(self.location_key(query), data, self.TTL_LOCATION_SEARCH)
    
    def get_country(self, country: str) -> Optional[Dict]:
        """Get cached country overview."""
        return self.get(self.country_key(country))
    
    def set_country(self, country: str, data: Dict) -> bool:
        """Cache country overview."""
        return self.set(self.country_key(country), data, self.TTL_COUNTRY_OVERVIEW)
    
    def get_nearby(self, lat: float, lng: float, radius: int) -> Optional[Dict]:
        """Get cached nearby search result."""
        return self.get(self.nearby_key(lat, lng, radius))
    
    def set_nearby(self, lat: float, lng: float, radius: int, data: Dict) -> bool:
        """Cache nearby search result."""
        return self.set(self.nearby_key(lat, lng, radius), data, self.TTL_NEARBY_SEARCH)
    
    def get_place(self, place_id: str) -> Optional[Dict]:
        """Get cached place detail."""
        return self.get(self.place_key(place_id))
    
    def set_place(self, place_id: str, data: Dict) -> bool:
        """Cache place detail."""
        return self.set(self.place_key(place_id), data, self.TTL_PLACE_DETAIL)
    
    def get_autocomplete(self, query: str) -> Optional[Dict]:
        """Get cached autocomplete result."""
        return self.get(self.autocomplete_key(query))
    
    def set_autocomplete(self, query: str, data: Dict) -> bool:
        """Cache autocomplete result."""
        return self.set(self.autocomplete_key(query), data, self.TTL_AUTOCOMPLETE)
    
    # ========== CACHE WARMING ==========
    
    def warm_popular_countries(
        self,
        countries: List[str],
        data_getter: callable
    ) -> int:
        """
        Pre-warm cache for popular countries.
        
        Args:
            countries: List of country names to warm
            data_getter: Function to get country data
        
        Returns:
            Number of countries warmed
        """
        warmed = 0
        for country in countries:
            try:
                key = self.country_key(country)
                if not self.get(key):
                    data = data_getter(country)
                    if data:
                        self.set(key, data, self.TTL_COUNTRY_OVERVIEW)
                        warmed += 1
            except Exception as e:
                logger.error(f"Error warming cache for {country}: {e}")
        return warmed
    
    # ========== STATISTICS ==========
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        if not self.client:
            return {'error': 'Redis client not available'}
        
        try:
            info = self.client.info('memory')
            keys = self.client.keys(f"{self.PREFIX}:*")
            
            return {
                'total_keys': len(keys),
                'memory_used': info.get('used_memory_human', 'unknown'),
                'prefix': self.PREFIX
            }
        except Exception as e:
            return {'error': str(e)}
    
    def clear_all(self) -> int:
        """Clear all places cache keys."""
        return self.invalidate_pattern("*")


# Module-level singleton for convenience
_cache_instance: Optional[PlacesCache] = None


def get_places_cache() -> PlacesCache:
    """Get or create the places cache singleton."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = PlacesCache()
    return _cache_instance
