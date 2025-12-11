"""
Places Integration Service - Phase 20
Integrates Places Engine with Group Planner for destination-based place search.

Features:
- 24-hour Redis cache for places by destination
- Returns places with lat/lng for map pins
- Pre-warms cache for popular destinations
- Zero Firestore reads on cache hit
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from Group_planner.cache_operations import GroupPlannerCacheOperations
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False

logger = logging.getLogger(__name__)


class PlacesIntegrationService:
    """
    Service for integrating Places Engine with Group Planner.
    
    Provides:
    - Destination search with 24h Redis cache
    - Place suggestions for trip planning
    - Coordinates for map rendering
    """
    
    CACHE_TTL = 86400  # 24 hours
    DEFAULT_LIMIT = 20
    
    def __init__(self, places_service=None, cache=None):
        """
        Initialize service.
        
        Args:
            places_service: PlacesService instance
            cache: Redis cache client
        """
        self._places_service = places_service
        self._cache = cache or (GroupPlannerCacheOperations() if CACHE_ENABLED else None)
    
    @property
    def places_service(self):
        """Lazy-load places service."""
        if self._places_service is None:
            try:
                from places_engine.services.places_service import PlacesService
                from firebase_admin import firestore
                db = firestore.client()
                self._places_service = PlacesService(db=db)
            except Exception as exc:
                logger.error("Failed to init PlacesService: %s", exc)
        return self._places_service
    
    def _get_cache_key(self, destination: str) -> str:
        """Generate cache key for destination."""
        normalized = '_'.join(destination.lower().split())
        return f"places:destination:{normalized}"
    
    def search_destination_places(
        self,
        destination: str,
        limit: int = None
    ) -> Dict[str, Any]:
        """
        Search for places at a destination.
        
        Uses 24-hour Redis cache. Only hits Firestore on cache miss.
        
        Args:
            destination: Destination name (e.g., "Bali, Indonesia", "Tokyo")
            limit: Max places to return (default 20)
            
        Returns:
            {
                "destination": "Bali, Indonesia",
                "coordinates": {"latitude": -8.4095, "longitude": 115.1889},
                "places": [...],
                "cache_hit": True/False
            }
        """
        limit = limit or self.DEFAULT_LIMIT
        cache_key = self._get_cache_key(destination)
        
        # Try cache first
        if self._cache and self._cache._is_available():
            try:
                cached = self._cache.redis_client.get(cache_key)
                if cached:
                    result = self._cache._safe_json_loads(cached)
                    if result:
                        result['cache_hit'] = True
                        logger.info("[PLACES][+] Cache hit for destination: %s", destination)
                        return result
            except Exception as exc:
                logger.warning("Cache read error: %s", exc)
        
        logger.info("[PLACES][-] Cache miss for destination: %s", destination)
        
        # Query Places Engine (1 Firestore query)
        if not self.places_service:
            return {
                'destination': destination,
                'coordinates': None,
                'places': [],
                'cache_hit': False,
                'error': 'Places service not available'
            }
        
        try:
            result = self.places_service.search_by_location(destination, limit=limit)
            
            if not result.get('success', False):
                return {
                    'destination': destination,
                    'coordinates': None,
                    'places': [],
                    'cache_hit': False,
                    'error': result.get('message', 'No places found')
                }
            
            # Extract and format places for trip planning
            places = []
            destination_coords = None
            
            for place in result.get('places', []):
                coords = place.get('coordinates', {})
                
                # Use first place's coordinates as destination center
                if not destination_coords and coords:
                    destination_coords = {
                        'latitude': coords.get('latitude'),
                        'longitude': coords.get('longitude')
                    }
                
                places.append({
                    'id': place.get('id'),
                    'name': place.get('name'),
                    'coordinates': {
                        'latitude': coords.get('latitude'),
                        'longitude': coords.get('longitude')
                    } if coords else None,
                    'city': place.get('city'),
                    'state': place.get('state'),
                    'country': place.get('country'),
                    'category': self._infer_category(place),
                    'rankScore': place.get('rank_score', 0),
                    'aiSummary': place.get('ai_summary'),
                    'photos': place.get('photos', {}),
                    'suggestedDuration': place.get('suggested_duration'),
                    'cost': place.get('cost')
                })
            
            response = {
                'destination': destination,
                'normalized': '_'.join(destination.lower().split()),
                'coordinates': destination_coords,
                'matchType': result.get('match_type'),
                'matched': result.get('matched'),
                'places': places,
                'count': len(places),
                'cache_hit': False,
                'cachedAt': datetime.utcnow().isoformat()
            }
            
            # Cache for 24 hours
            if self._cache and self._cache._is_available() and places:
                try:
                    self._cache.redis_client.setex(
                        cache_key,
                        self.CACHE_TTL,
                        self._cache._safe_json_dumps(response)
                    )
                    logger.info("[PLACES][S] Cached %d places for: %s", len(places), destination)
                except Exception as exc:
                    logger.warning("Cache write error: %s", exc)
            
            return response
            
        except Exception as exc:
            logger.error("Places search error: %s", exc)
            return {
                'destination': destination,
                'coordinates': None,
                'places': [],
                'cache_hit': False,
                'error': str(exc)
            }
    
    def get_destination_coordinates(self, destination: str) -> Optional[Dict]:
        """
        Get coordinates for a destination.
        
        Uses cached places data if available.
        
        Args:
            destination: Destination name
            
        Returns:
            {"latitude": float, "longitude": float} or None
        """
        result = self.search_destination_places(destination, limit=1)
        return result.get('coordinates')
    
    def get_popular_destinations(self) -> List[Dict]:
        """
        Get list of popular destinations with place counts.
        
        Uses countries collection.
        """
        try:
            if not self.places_service:
                return []
            
            result = self.places_service.get_all_countries()
            if result.get('success'):
                return result.get('countries', [])[:20]
            return []
            
        except Exception as exc:
            logger.error("Failed to get popular destinations: %s", exc)
            return []
    
    def prewarm_cache(self, destinations: List[str]) -> int:
        """
        Pre-warm cache for popular destinations.
        
        Call during off-peak hours.
        
        Args:
            destinations: List of destination names
            
        Returns:
            Number of destinations cached
        """
        warmed = 0
        
        for dest in destinations:
            try:
                result = self.search_destination_places(dest)
                if result.get('places'):
                    warmed += 1
                    logger.info("[PREWARM] Cached places for: %s", dest)
            except Exception as exc:
                logger.warning("[PREWARM] Failed for %s: %s", dest, exc)
        
        return warmed
    
    def _infer_category(self, place: Dict) -> str:
        """Infer place category from tags."""
        tags = place.get('tags', [])
        
        if not tags:
            return 'attraction'
        
        tag_lower = [t.lower() for t in tags]
        
        if any(t in tag_lower for t in ['restaurant', 'food', 'dining', 'cafe']):
            return 'restaurant'
        if any(t in tag_lower for t in ['hotel', 'accommodation', 'resort', 'hostel']):
            return 'hotel'
        if any(t in tag_lower for t in ['shopping', 'market', 'mall']):
            return 'shopping'
        if any(t in tag_lower for t in ['transport', 'airport', 'station']):
            return 'transport'
        if any(t in tag_lower for t in ['hiking', 'activity', 'adventure', 'sport']):
            return 'activity'
        
        return 'attraction'


# Popular destinations for pre-warming
POPULAR_DESTINATIONS = [
    "Tokyo, Japan",
    "Bali, Indonesia",
    "Paris, France",
    "London, United Kingdom",
    "New York, USA",
    "Rome, Italy",
    "Barcelona, Spain",
    "Sydney, Australia",
    "Bangkok, Thailand",
    "Dubai, UAE",
    "Singapore",
    "Hong Kong",
    "Seoul, South Korea",
    "Amsterdam, Netherlands",
    "Prague, Czech Republic",
    "Santorini, Greece",
    "Maui, Hawaii",
    "Cancun, Mexico",
    "Phuket, Thailand",
    "Queenstown, New Zealand"
]
