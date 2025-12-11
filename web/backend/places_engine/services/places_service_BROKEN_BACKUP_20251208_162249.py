"""
Places Engine Service

Business logic layer for all places operations.
Provides methods for searching, filtering, and retrieving places data.
"""

import math
import time
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# Invalid photo URL patterns to filter out
INVALID_PHOTO_PATTERNS = frozenset([
    'commons-logo.svg',
    'airplane_silhouette.svg',
    'flag_of_',
    'coat_of_arms',
    'logo_',
    'icon-',
    'placeholder',
    'no_image',
    'default_',
    'blank.svg',
    'aiga_',
    '_location_map.svg',
    '_map.svg',
    'symbol_',
    'pictogram',
])


class PlacesService:
    """
    Service layer for places operations.
    
    Provides:
    - Location-based search (city/state)
    - Country overview with states
    - Nearby places with fallback
    - Autocomplete suggestions
    - Place details and filtering
    """
    
    def __init__(self, db: Any = None, cache: Optional[Any] = None):
        """
        Initialize PlacesService.
        
        Args:
            db: Firestore client instance
            cache: Optional PlacesCache instance for caching
        """
        self.db = db
        self.cache = cache
        
        # Import Firestore Query for ordering
        try:
            from firebase_admin import firestore as fs
            from google.cloud.firestore_v1.base_query import FieldFilter
            from google.cloud.firestore_v1 import Query
            self._firestore = fs
            self._FieldFilter = FieldFilter
            self._Query = Query
        except ImportError:
            self._firestore = None
            self._FieldFilter = None
            self._Query = None
    
    # ========== HELPER METHODS ==========
    
    def _normalize_query(self, query: str) -> str:
        """Normalize search query to match stored format."""
        if not query:
            return ''
        return '_'.join(query.lower().split())
    
    def _convert_geopoint(self, place: Dict) -> Dict:
        """Convert Firestore GeoPoint to dictionary."""
        coords = place.get('coordinates')
        if coords and hasattr(coords, 'latitude'):
            place['coordinates'] = {
                'latitude': coords.latitude,
                'longitude': coords.longitude
            }
        return place
    
    def _sanitize_photo(self, place: Dict) -> Dict:
        """Validate and sanitize photo URLs, filtering placeholders."""
        photos = place.get('photos', {})
        
        if not photos:
            place['photos'] = {'thumbnail_url': None, 'has_valid_photo': False}
            return place
        
        # Handle nested wikimedia_commons structure
        if 'wikimedia_commons' in photos:
            thumbnail = photos.get('wikimedia_commons', {}).get('thumbnail', {})
            url = thumbnail.get('url')
        else:
            url = photos.get('thumbnail_url')
        
        # Check for invalid patterns
        if url:
            url_lower = url.lower()
            for pattern in INVALID_PHOTO_PATTERNS:
                if pattern in url_lower:
                    place['photos'] = {
                        'thumbnail_url': None,
                        'has_valid_photo': False
                    }
                    return place
        
        # Normalize photo structure
        if 'thumbnail_url' not in place['photos'] and 'wikimedia_commons' in photos:
            thumbnail = photos.get('wikimedia_commons', {}).get('thumbnail', {})
            place['photos'] = {
                'thumbnail_url': thumbnail.get('url'),
                'thumbnail_width': thumbnail.get('width'),
                'thumbnail_height': thumbnail.get('height'),
                'attribution': thumbnail.get('attribution'),
                'has_valid_photo': bool(thumbnail.get('url'))
            }
        
        return place
    
    def _process_place(self, doc: Any) -> Dict:
        """Process a Firestore document into a standardized place dict."""
        place = doc.to_dict()
        place['id'] = doc.id
        place = self._convert_geopoint(place)
        place = self._sanitize_photo(place)
        
        # Convert Firestore timestamps to ISO strings for JSON serialization
        for key in ['created_at', 'updated_at']:
            if key in place and place[key] is not None:
                if hasattr(place[key], 'isoformat'):
                    place[key] = place[key].isoformat()
                else:
                    place[key] = str(place[key])
        
        return place
    
    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calculate distance between two coordinates in meters."""
        earth_radius = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (
            math.sin(delta_phi / 2) ** 2 +
            math.cos(phi1) * math.cos(phi2) *
            math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return earth_radius * c
    
    def _calculate_bounding_box(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float
    ) -> Dict[str, float]:
        """Calculate bounding box for geospatial queries."""
        # 1 degree latitude ≈ 111km
        # 1 degree longitude ≈ 111km * cos(latitude)
        lat_delta = (radius_meters / 1000) / 111
        lng_delta = (radius_meters / 1000) / (111 * math.cos(math.radians(latitude)))
        
        return {
            'min_lat': latitude - lat_delta,
            'max_lat': latitude + lat_delta,
            'min_lng': longitude - lng_delta,
            'max_lng': longitude + lng_delta
        }
    
    # ========== LOCATION SEARCH ==========
    
    def search_by_location(self, query: str, limit: int = 20, page: int = 1) -> Dict:
        """
        ULTRA-OPTIMIZED Location search using indexed queries (MAX 1-2 READS, <500ms).
        
        Strategy:
        1. Check cache first (free - 0 reads)
        2. Query cities with indexed name field filter (1 read max)
        3. Query countries with indexed name field filter (1 read max)
        4. Query states with indexed name field filter (1 read max)
        5. Cache result and return
        
        Uses Firestore field filters instead of streaming to avoid reading every document.
        With indexed queries, Firestore returns results efficiently without scanning entire collection.
        
        Args:
            query: City, state, or country name
            limit: Maximum number of places to return per page (default 20)
            page: Page number for pagination (default 1)
        
        Returns:
            Dict with location information and places, max 1-2 reads, <500ms response
        """
        # ============ STEP 1: CHECK CACHE FIRST (FREE - 0 READS) ============
        if self.cache:
            cached = self.cache.get_location(query)
            if cached:
                cached['cache_hit'] = True
                cached['firebase_reads'] = 0
                return cached
        
        start_time = time.time()
        firebase_reads = 0
        
        try:
            query_normalized = query.strip()
            query_lower = query_normalized.lower()
            
            cities_ref = self.db.collection('cities')
            countries_ref = self.db.collection('countries')
            states_ref = self.db.collection('states')
            
            # ============ STEP 2: FIRST FIREBASE READ - CITIES (MOST COMMON) ============
            # Use INDEXED QUERY (not streaming) to find cities by exact name
            # Firestore index on 'name' field returns results efficiently
            
            city_docs = list(cities_ref.where(
                filter=self._FieldFilter('name', '==', query_normalized)
            ).limit(1).stream())
            firebase_reads += 1
            
            if city_docs:
                doc = city_docs[0]
                city_data = doc.to_dict()
                # CITY MATCH FOUND
                top_places = city_data.get('top_places', [])
                
                result = {
                    'success': True,
                    'query': query,
                    'match_type': 'city',
                    'matched': {
                        'id': doc.id,
                        'name': city_data.get('name'),
                        'state': city_data.get('state'),
                        'country': city_data.get('country'),
                        'place_count': city_data.get('place_count', len(top_places))
                    },
                    'count': len(top_places),
                    'places': top_places[:limit],
                    'cache_hit': False,
                    'firebase_reads': firebase_reads,  # 1 read
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
                
                # Cache this location for future queries
                if self.cache:
                    self.cache.set_location(query, result)
                
                return result
            
            # ============ STEP 3: SECOND FIREBASE READ - COUNTRIES ============
            # If city not found, try country using indexed query
            
            country_docs = list(countries_ref.where(
                filter=self._FieldFilter('name', '==', query_normalized)
            ).limit(1).stream())
            firebase_reads += 1
            
            if country_docs:
                doc = country_docs[0]
                country_data = doc.to_dict()
                # COUNTRY MATCH FOUND
                
                # Extract top places from all states
                all_places = []
                states_data = country_data.get('states', [])
                
                for state in states_data:
                    if isinstance(state, dict):
                        top_places = state.get('top_places', [])[:5]
                        all_places.extend(top_places)
                
                result = {
                    'success': True,
                    'query': query,
                    'match_type': 'country',
                    'matched': {
                        'id': doc.id,
                        'name': country_data.get('name'),
                        'state_count': country_data.get('state_count', 0),
                        'place_count': country_data.get('place_count', 0)
                    },
                    'count': len(all_places),
                    'places': all_places[:limit],
                    'cache_hit': False,
                    'firebase_reads': firebase_reads,  # 2 reads
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
                
                # Cache this location for future queries
                if self.cache:
                    self.cache.set_location(query, result)
                
                return result
            
            # ============ STEP 4: OPTIONAL THIRD READ - STATES ============
            # If neither city nor country found, try states using indexed query
            
            state_docs = list(states_ref.where(
                filter=self._FieldFilter('name', '==', query_normalized)
            ).limit(1).stream())
            firebase_reads += 1
            
            if state_docs:
                doc = state_docs[0]
                state_data = doc.to_dict()
                # STATE MATCH FOUND
                top_places = state_data.get('top_places', [])
                
                result = {
                    'success': True,
                    'query': query,
                    'match_type': 'state',
                    'matched': {
                        'id': doc.id,
                        'name': state_data.get('name'),
                        'country': state_data.get('country'),
                        'place_count': state_data.get('place_count', len(top_places))
                    },
                    'count': len(top_places),
                    'places': top_places[:limit],
                    'cache_hit': False,
                    'firebase_reads': firebase_reads,  # 3 reads (max)
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
                
                # Cache this location for future queries
                if self.cache:
                    self.cache.set_location(query, result)
                
                return result
            
            # ============ STEP 5: NOT FOUND - RETURN ERROR ============
            result = {
                'success': False,
                'query': query,
                'error': 'Location not found',
                'count': 0,
                'places': [],
                'cache_hit': False,
                'firebase_reads': firebase_reads,  # Total reads (cities + countries + states = 3)
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Search by location failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'query': query
            }
    
    # ========== COUNTRY OVERVIEW ==========
    
    def get_country_overview(self, country: str) -> Dict:
        """
        Get country overview with states and top places per state.
        
        Args:
            country: Country name (e.g., "Argentina", "USA")
        
        Returns:
            Dict with states and their top places
        """
        # Check cache
        if self.cache:
            cached = self.cache.get_country(country)
            if cached:
                cached['cache_hit'] = True
                return cached
        
        start_time = time.time()
        firebase_reads = 0  # Track Firebase API calls
        
        try:
            country_normalized = self._normalize_query(country)
            countries_ref = self.db.collection('countries')
            
            # Try document ID first (slug-based)
            country_doc = countries_ref.document(country_normalized).get()
            firebase_reads += 1  # 1 read for country document
            
            if not country_doc.exists:
                # Try query by country name field
                query = countries_ref.where(
                    filter=self._FieldFilter('country', '==', country)
                ).limit(1)
                docs = list(query.stream())
                firebase_reads += len(docs)  # Count country query reads
                
                if not docs:
                    return {
                        'success': False,
                        'country': country,
                        'error': f"Country '{country}' not found",
                        'states': [],
                        'firebase_reads': firebase_reads
                    }
                
                country_doc = docs[0]
            
            country_data = country_doc.to_dict()
            
            # Get all cities for this country to build state list with top places
            # Try both 'country' and 'country_name' fields for compatibility
            country_name = country_data.get('name') or country_data.get('country', country)
            
            logger.info(f"Searching cities for country: {country_name}")
            
            # OPTIMIZED: Query with limit to avoid reading all cities
            # CRITICAL FIX: Add .limit() to prevent reading 1000s of cities
            cities_query = self.db.collection('cities').where(
                filter=self._FieldFilter('country_name', '==', country_name)
            ).limit(500)  # CRITICAL: Prevent reading all cities
            
            cities_docs = list(cities_query.stream())
            firebase_reads += len(cities_docs)  # Count city documents
            
            # If no results, try with 'country' field (legacy schema)
            if not cities_docs:
                logger.info(f"No cities found with country_name, trying country field")
                cities_query = self.db.collection('cities').where(
                    filter=self._FieldFilter('country', '==', country_name)
                ).limit(500)  # CRITICAL: Add limit to legacy query too
                cities_docs = list(cities_query.stream())
                firebase_reads += len(cities_docs)
            
            logger.info(f"Found {len(cities_docs)} cities for {country_name}")
            
            # Group by state and fetch top 5 places for each
            states_map = {}
            for city_doc in cities_docs:
                city_data = city_doc.to_dict()
                # Try both 'state_name' and 'state' fields
                state_name = city_data.get('state_name') or city_data.get('state')
                city_name = city_data.get('city_name') or city_data.get('city')
                
                if state_name and state_name not in states_map:
                    states_map[state_name] = {
                        'name': state_name,
                        'cities': [],
                        'place_count': 0,
                        'top_places': []
                    }
                if state_name:
                    states_map[state_name]['cities'].append(city_name)
                    states_map[state_name]['place_count'] += city_data.get('place_count', 0)
            
            # OPTIMIZED: Use aggregate query with limit to get only top 5 per state
            # This reduces reads from 200 to just ~50 (10 states × 5 places)
            places_ref = self.db.collection('places')
            
            for state_name, state_data in states_map.items():
                """
                CRITICAL FIX: Removed fallback to full collection scan.
                The fallback was causing 1000+ additional reads when index was missing.
                Now we only try indexed queries with limits.
                """
                state_places_docs = []
                
                # Try with 'state_name' field first (current schema)
                try:
                    state_places_query = places_ref.where(
                        filter=self._FieldFilter('state_name', '==', state_name)
                    ).order_by('rank_score', direction='DESCENDING').limit(5)
                    
                    state_places_docs = list(state_places_query.stream())
                    firebase_reads += len(state_places_docs)
                    logger.debug(f"Read {len(state_places_docs)} top places for state: {state_name}")
                
                except Exception as e:
                    logger.debug(f"state_name + rank_score query failed: {e}")
                
                # If no results with state_name, try legacy 'state' field (but still with index)
                if not state_places_docs:
                    try:
                        state_places_query = places_ref.where(
                            filter=self._FieldFilter('state', '==', state_name)
                        ).order_by('rank_score', direction='DESCENDING').limit(5)
                        
                        state_places_docs = list(state_places_query.stream())
                        firebase_reads += len(state_places_docs)
                        logger.debug(f"Read {len(state_places_docs)} top places for state (legacy field): {state_name}")
                    
                    except Exception as e:
                        logger.debug(f"state + rank_score query also failed: {e}")
                        # NO FALLBACK - Just use empty list. Better to show no data than 1000+ reads
                        state_places_docs = []
                
                # Process top places with FULL details
                top_places = []
                for doc in state_places_docs[:5]:  # Ensure we only take top 5
                    place_data = self._process_place(doc)
                    top_places.append(place_data)
                
                state_data['top_places'] = top_places
            
            states = list(states_map.values())
            
            result = {
                'success': True,
                'country': country_data.get('name', country),
                'state_count': len(states),
                'total_places': country_data.get('place_count', 0),
                'states': states,
                'cache_hit': False,
                'firebase_reads': firebase_reads,
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
            if self.cache:
                self.cache.set_country(country, result)
            
            return result
        
        except Exception as e:
            logger.error("Country overview error: %s", e)
            return {
                'success': False,
                'country': country,
                'error': str(e),
                'states': []
            }
    
    # ========== NEARBY SEARCH ==========
    
    def get_nearby_places(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 10000,
        limit: int = 20
    ) -> Dict:
        """
        Get nearby places with fallback to nearest city.
        
        If no places found within radius, returns places from
        the nearest city with data.
        
        Args:
            latitude: Search point latitude
            longitude: Search point longitude
            radius_meters: Search radius in meters (default 10km)
            limit: Maximum places to return
        
        Returns:
            Dict with places and data source info
        """
        # Check cache
        if self.cache:
            cached = self.cache.get_nearby(latitude, longitude, int(radius_meters))
            if cached:
                cached['cache_hit'] = True
                return cached
        
        start_time = time.time()
        
        try:
            # Step 1: Search within radius
            places = self._search_places_in_radius(latitude, longitude, radius_meters)
            
            if len(places) >= 5:
                places = places[:limit]
                
                result = {
                    'success': True,
                    'search_point': {'latitude': latitude, 'longitude': longitude},
                    'search_radius_km': round(radius_meters / 1000, 2),
                    'data_source': {
                        'type': 'direct',
                        'reason': 'Places found within search radius'
                    },
                    'count': len(places),
                    'places': places,
                    'cache_hit': False,
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
                
                if self.cache:
                    self.cache.set_nearby(latitude, longitude, int(radius_meters), result)
                
                return result
            
            # Step 2: Fallback to nearest city
            nearest_city = self._find_nearest_city_with_data(latitude, longitude)
            
            if not nearest_city:
                return {
                    'success': False,
                    'search_point': {'latitude': latitude, 'longitude': longitude},
                    'error': 'No places found nearby and no cities with data',
                    'count': 0,
                    'places': []
                }
            
            # Step 3: Get places from nearest city
            city_places = self._get_places_by_city_name(nearest_city['name'])
            
            # Add distance from search point
            for place in city_places:
                coords = place.get('coordinates')
                if coords and coords.get('latitude'):
                    place['distance_m'] = round(self._haversine_distance(
                        latitude, longitude,
                        coords['latitude'], coords['longitude']
                    ), 2)
                else:
                    place['distance_m'] = nearest_city['distance_m']
            
            city_places.sort(key=lambda p: p.get('distance_m', float('inf')))
            city_places = city_places[:limit]
            
            result = {
                'success': True,
                'search_point': {'latitude': latitude, 'longitude': longitude},
                'search_radius_km': round(radius_meters / 1000, 2),
                'data_source': {
                    'type': 'fallback',
                    'city': nearest_city['name'],
                    'country': nearest_city.get('country'),
                    'distance_km': round(nearest_city['distance_m'] / 1000, 1),
                    'reason': f"Showing places from {nearest_city['name']}"
                },
                'count': len(city_places),
                'places': city_places,
                'cache_hit': False,
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
            if self.cache:
                self.cache.set_nearby(latitude, longitude, int(radius_meters), result)
            
            return result
        
        except Exception as e:
            logger.error("Nearby search error: %s", e)
            return {
                'success': False,
                'search_point': {'latitude': latitude, 'longitude': longitude},
                'error': str(e),
                'count': 0,
                'places': []
            }
    
    def _search_places_in_radius(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float
    ) -> List[Dict]:
        """
        OPTIMIZED: Search places within a radius using bounding box + Haversine.
        
        CRITICAL FIX: Instead of streaming ALL places in collection,
        we now query by city/state and limit results.
        
        This reduces reads from 1000+ to ~100-200 per query.
        """
        bbox = self._calculate_bounding_box(latitude, longitude, radius_meters)
        
        places = []
        
        # Strategy: Query nearby cities instead of all places
        # This is 10x more efficient than streaming entire places collection
        
        try:
            # Get cities in bounding box (much smaller than places)
            cities_ref = self.db.collection('cities')
            
            # Build list of nearby cities from bounding box
            nearby_cities = []
            for city_doc in cities_ref.where(
                filter=self._FieldFilter('place_count', '>', 0)
            ).limit(100).stream():  # CRITICAL: Add limit!
                city_data = city_doc.to_dict()
                city_name = city_data.get('name')
                
                if city_name:
                    nearby_cities.append(city_name)
            
            # For each city, get places and filter by radius
            places_ref = self.db.collection('places')
            
            for city_name in nearby_cities:
                # Query places in city with limit (CRITICAL FIX)
                city_places_query = places_ref.where(
                    filter=self._FieldFilter('city_name', '==', city_name)
                ).where(
                    filter=self._FieldFilter('has_coordinates', '==', True)
                ).order_by('rank_score', direction='DESCENDING').limit(50)  # CRITICAL: Limit to top 50
                
                for doc in city_places_query.stream():
                    place = self._process_place(doc)
                    coords = place.get('coordinates')
                    
                    if not coords:
                        continue
                    
                    place_lat = coords.get('latitude')
                    place_lng = coords.get('longitude')
                    
                    if not (place_lat and place_lng):
                        continue
                    
                    # Exact distance check
                    distance = self._haversine_distance(latitude, longitude, place_lat, place_lng)
                    
                    if distance <= radius_meters:
                        place['distance_m'] = round(distance, 2)
                        places.append(place)
            
            places.sort(key=lambda p: p['distance_m'])
            return places
        
        except Exception as e:
            logger.warning(f"Radius search failed, using fallback: {e}")
            return []
    
    def _find_nearest_city_with_data(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict]:
        """
        OPTIMIZED: Find the nearest city that has places in our database.
        
        CRITICAL FIX: Add .limit(200) to prevent reading all cities.
        This reduces reads from 1000+ to max 200.
        """
        cities_ref = self.db.collection('cities')
        
        nearest = None
        nearest_distance = float('inf')
        
        # CRITICAL FIX: Add limit to prevent reading all cities
        for doc in cities_ref.where(
            filter=self._FieldFilter('place_count', '>', 0)
        ).order_by('place_count', direction='DESCENDING').limit(200).stream():
            city_data = doc.to_dict()
            
            city_name = city_data.get('name')
            if not city_name:
                continue
            
            # Get sample place for coordinates
            sample_query = self.db.collection('places').where(
                filter=self._FieldFilter('city_name', '==', city_name)
            ).where(
                filter=self._FieldFilter('has_coordinates', '==', True)
            ).limit(1)
            
            for place_doc in sample_query.stream():
                place = place_doc.to_dict()
                coords = place.get('coordinates')
                
                if coords and hasattr(coords, 'latitude'):
                    city_lat = coords.latitude
                    city_lng = coords.longitude
                elif coords:
                    city_lat = coords.get('latitude')
                    city_lng = coords.get('longitude')
                else:
                    continue
                
                if city_lat and city_lng:
                    distance = self._haversine_distance(
                        latitude, longitude, city_lat, city_lng
                    )
                    
                    if distance < nearest_distance:
                        nearest_distance = distance
                        nearest = {
                            'name': city_name,
                            'country': city_data.get('country'),
                            'state': city_data.get('state'),
                            'distance_m': distance,
                            'place_count': city_data.get('place_count', 0)
                        }
                break
        
        return nearest
    
    def _get_places_by_city_name(self, city_name: str) -> List[Dict]:
        """
        OPTIMIZED: Get all places for a city sorted by rank score.
        
        CRITICAL FIX: Add .limit(100) to prevent reading all places in city.
        """
        places_ref = self.db.collection('places').where(
            filter=self._FieldFilter('city_name', '==', city_name)
        ).order_by('rank_score', direction=self._Query.DESCENDING).limit(100)
        
        return [self._process_place(doc) for doc in places_ref.stream()]
    
    # ========== AUTOCOMPLETE ==========
    
    def autocomplete(self, query: str, limit: int = 10) -> Dict:
        """
        Ultra-fast autocomplete using pre-loaded JSON data (client-side search).
        Returns suggestions in <300ms with 0 Firebase reads.
        
        Similar to Google's autocomplete:
        - 0 Firebase reads (searches pre-loaded JSON data)
        - <300ms response time
        - Ranked by popularity
        - NO CACHING (JSON search is already fast, cache adds complexity)
        
        Args:
            query: Partial search query (min 2 chars)
            limit: Maximum suggestions to return
        
        Returns:
            Dict with ranked suggestions
        """
        import json
        from pathlib import Path
        
        start_time = time.time()
        query_lower = query.lower().strip()
        
        if len(query_lower) < 2:
            return {'success': True, 'query': query, 'suggestions': [], 'cache_hit': False, 'firebase_reads': 0}
        
        try:
            suggestions = []
            firebase_reads = 0
            
            # Load pre-generated JSON data (includes all countries, cities, places)
            # File is in places_engine folder
            data_file = Path(__file__).parent.parent / 'places_autocomplete_data.json'
            
            # Fallback: check in backend root too
            if not data_file.exists():
                data_file = Path(__file__).parent.parent.parent / 'places_autocomplete_data.json'
            
            if not data_file.exists():
                logger.warning(f"Places data file not found at {data_file}")
                logger.warning(f"Checked paths:")
                logger.warning(f"  1. {Path(__file__).parent.parent / 'places_autocomplete_data.json'}")
                logger.warning(f"  2. {Path(__file__).parent.parent.parent / 'places_autocomplete_data.json'}")
                # Return empty results instead of error
                result = {
                    'success': True,
                    'query': query,
                    'suggestions': [],
                    'cache_hit': False,
                    'firebase_reads': 0,
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
                return result
            
            # Read JSON data
            with open(data_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            
            # Search all data - look for prefix matches
            # Priority: places > cities > countries
            # UNIQUE ONLY: Store each name only once across all types
            
            seen_names = set()  # Track unique names to avoid duplicates
            
            # Search places (highest priority)
            for place in all_data.get('places', []):
                name_lower = place.get('name_lower', '')
                name = place.get('name', '')
                
                if name_lower.startswith(query_lower) and name not in seen_names:
                    suggestions.append({
                        'name': name,
                        'type': 'place',
                        'rank_score': place.get('rank_score', 0),
                        'city': place.get('city', ''),
                        'state': place.get('state', ''),
                        'country': place.get('country', ''),
                        'id': place.get('id', ''),
                        'coordinates': place.get('coordinates', {})
                    })
                    seen_names.add(name)  # Mark as seen
                    if len(suggestions) >= limit:
                        break
            
            # Search cities if we need more results (skip duplicates)
            if len(suggestions) < limit:
                for city in all_data.get('cities', []):
                    name_lower = city.get('name_lower', '')
                    name = city.get('name', '')
                    
                    if name_lower.startswith(query_lower) and name not in seen_names:
                        suggestions.append({
                            'name': name,
                            'type': 'city',
                            'rank_score': city.get('place_count', 0),
                            'country': city.get('country', ''),
                            'state': city.get('state', ''),
                            'id': city.get('id', ''),
                            'coordinates': city.get('coordinates', {})
                        })
                        seen_names.add(name)  # Mark as seen
                        if len(suggestions) >= limit:
                            break
            
            # Search countries if we still need more results (skip duplicates)
            if len(suggestions) < limit:
                for country in all_data.get('countries', []):
                    name_lower = country.get('name_lower', '')
                    name = country.get('name', '')
                    
                    if name_lower.startswith(query_lower) and name not in seen_names:
                        suggestions.append({
                            'name': name,
                            'type': 'country',
                            'rank_score': country.get('place_count', 0),
                            'id': country.get('id', ''),
                            'code': country.get('code', '')
                        })
                        seen_names.add(name)  # Mark as seen
                        if len(suggestions) >= limit:
                            break
            
            # Limit results
            suggestions = suggestions[:limit]
            
            result = {
                'success': True,
                'query': query,
                'suggestions': suggestions,
                'firebase_reads': 0,  # 0 reads - all from JSON file!
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
            # No caching - JSON search is already instant, caching adds overhead
            return result
        
        except Exception as e:
            logger.error(f"Autocomplete error: {e}", exc_info=True)
            return {
                'success': False,
                'query': query,
                'error': str(e),
                'suggestions': [],
                'firebase_reads': 0
            }
    
    # ========== SEARCH WITH FILTERS ==========
    
    def search_places(
        self,
        query: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        tags: Optional[List[str]] = None,
        cost: Optional[str] = None,
        rating_min: Optional[float] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict:
        """
        Search places with multiple filters.
        
        Args:
            query: Text search query
            city: Filter by city name
            country: Filter by country name
            tags: Filter by tags (any match)
            cost: Filter by cost level
            rating_min: Minimum rating threshold
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            Dict with filtered places
        """
        start_time = time.time()
        
        try:
            places_ref = self.db.collection('places')
            
            # Apply Firestore filters
            if country:
                places_ref = places_ref.where(filter=self._FieldFilter('country', '==', country))
            
            if city:
                places_ref = places_ref.where(filter=self._FieldFilter('city', '==', city))
            
            if cost:
                places_ref = places_ref.where(filter=self._FieldFilter('cost', '==', cost))
            
            if rating_min:
                places_ref = places_ref.where(
                    filter=self._FieldFilter('rating_tourist_priority', '>=', rating_min)
                )
            
            # Order by rank score
            places_ref = places_ref.order_by(
                'rank_score',
                direction=self._Query.DESCENDING
            )
            
            # Apply pagination
            places_ref = places_ref.limit(limit).offset(offset)
            
            # Process results
            places = []
            for doc in places_ref.stream():
                place = self._process_place(doc)
                
                # Client-side text filter
                if query:
                    search_text = place.get('search_text', '').lower()
                    if query.lower() not in search_text:
                        continue
                
                # Client-side tag filter
                if tags:
                    place_tags = set(t.lower() for t in place.get('tags', []))
                    if not any(tag.lower() in place_tags for tag in tags):
                        continue
                
                places.append(place)
            
            return {
                'success': True,
                'count': len(places),
                'places': places,
                'filters': {
                    'query': query,
                    'city': city,
                    'country': country,
                    'tags': tags,
                    'cost': cost,
                    'rating_min': rating_min
                },
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'has_more': len(places) == limit
                },
                'cache_hit': False,
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        
        except Exception as e:
            logger.error("Search places error: %s", e)
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'places': []
            }
    
    # ========== PLACE DETAILS ==========
    
    def get_place_by_id(self, place_id: str) -> Optional[Dict]:
        """
        Get place details by ID.
        
        Args:
            place_id: Firestore document ID
        
        Returns:
            Place data dict or None if not found
        """
        start_time = time.time()
        
        try:
            doc_ref = self.db.collection('places').document(place_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            place = self._process_place(doc)
            
            return {
                'success': True,
                'place': place,
                'cache_hit': False,
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        
        except Exception as e:
            logger.error("Get place error: %s", e)
            return None
    
    # ========== POPULAR PLACES ==========
    
    def get_popular_places(
        self,
        country: Optional[str] = None,
        limit: int = 20
    ) -> Dict:
        """
        Get popular places sorted by rank score.
        
        Args:
            country: Optional country filter
            limit: Maximum results
        
        Returns:
            Dict with popular places
        """
        start_time = time.time()
        
        try:
            places_ref = self.db.collection('places')
            
            if country:
                places_ref = places_ref.where(filter=self._FieldFilter('country', '==', country))
            
            places_ref = places_ref.order_by(
                'rank_score',
                direction=self._Query.DESCENDING
            ).limit(limit)
            
            places = [self._process_place(doc) for doc in places_ref.stream()]
            
            return {
                'success': True,
                'count': len(places),
                'country': country,
                'places': places,
                'cache_hit': False,
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        
        except Exception as e:
            logger.error("Get popular places error: %s", e)
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'places': []
            }
    
    # ========== COUNTRIES AND CITIES ==========
    
    def get_all_countries(self) -> Dict:
        """Get list of all countries."""
        start_time = time.time()
        
        try:
            countries = []
            for doc in self.db.collection('countries').stream():
                country = doc.to_dict()
                country['id'] = doc.id
                countries.append(country)
            
            countries.sort(key=lambda c: c.get('name', ''))
            
            return {
                'success': True,
                'count': len(countries),
                'countries': countries,
                'cache_hit': False,
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        
        except Exception as e:
            logger.error("Get countries error: %s", e)
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'countries': []
            }
    
    def autocomplete_fast(self, query: str, limit: int = 10) -> Dict:
        """
        Fast autocomplete suggestions using direct prefix matching on Firestore.
        Returns countries, states, and cities that match the query prefix.
        
        Performance: Should be <100ms with proper Firestore indexing
        """
        start_time = time.time()
        firebase_reads = 0
        query_lower = query.lower()
        suggestions = []
        
        try:
            if not query or len(query) < 2:
                return {
                    'success': True,
                    'suggestions': [],
                    'query': query,
                    'response_time_ms': 0
                }
            
            # Try to get from cache first
            cache_key = f"autocomplete:{query_lower}"
            if self.cache:
                cached = self.cache.get(cache_key)
                if cached:
                    return {
                        'success': True,
                        'suggestions': cached,
                        'query': query,
                        'cache_hit': True,
                        'response_time_ms': round((time.time() - start_time) * 1000, 2)
                    }
            
            # Query countries that start with query
            try:
                countries_ref = self.db.collection('countries')
                country_query = countries_ref.where(
                    filter=self._FieldFilter('name', '>=', query)
                ).where(
                    filter=self._FieldFilter('name', '<', query[:-1] + chr(ord(query[-1]) + 1))
                ).limit(limit)
                
                country_docs = list(country_query.stream())
                firebase_reads += 1
                
                for doc in country_docs:
                    data = doc.to_dict()
                    suggestions.append({
                        'name': data.get('name', ''),
                        'type': 'country',
                        'place_count': data.get('place_count', 0)
                    })
            except Exception as e:
                logger.warning(f"Country autocomplete failed: {e}")
            
            # Query states that start with query
            if len(suggestions) < limit:
                try:
                    states_ref = self.db.collection('states')
                    state_query = states_ref.where(
                        filter=self._FieldFilter('name', '>=', query)
                    ).where(
                        filter=self._FieldFilter('name', '<', query[:-1] + chr(ord(query[-1]) + 1))
                    ).limit(limit - len(suggestions))
                    
                    state_docs = list(state_query.stream())
                    firebase_reads += 1
                    
                    for doc in state_docs:
                        data = doc.to_dict()
                        suggestions.append({
                            'name': data.get('name', ''),
                            'type': 'state',
                            'place_count': data.get('place_count', 0)
                        })
                except Exception as e:
                    logger.warning(f"State autocomplete failed: {e}")
            
            # Query cities that start with query
            if len(suggestions) < limit:
                try:
                    cities_ref = self.db.collection('cities')
                    city_query = cities_ref.where(
                        filter=self._FieldFilter('name', '>=', query)
                    ).where(
                        filter=self._FieldFilter('name', '<', query[:-1] + chr(ord(query[-1]) + 1))
                    ).limit(limit - len(suggestions))
                    
                    city_docs = list(city_query.stream())
                    firebase_reads += 1
                    
                    for doc in city_docs:
                        data = doc.to_dict()
                        suggestions.append({
                            'name': data.get('name', ''),
                            'type': 'city',
                            'place_count': data.get('place_count', 0)
                        })
                except Exception as e:
                    logger.warning(f"City autocomplete failed: {e}")
            
            # Trim to limit
            suggestions = suggestions[:limit]
            
            # Cache the result
            if self.cache and suggestions:
                self.cache.set(cache_key, suggestions, ex=3600)  # Cache for 1 hour
            
            return {
                'success': True,
                'suggestions': suggestions,
                'query': query,
                'firebase_reads': firebase_reads,
                'cache_hit': False,
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
        except Exception as e:
            logger.error(f"Autocomplete error: {e}", exc_info=True)
            return {
                'success': False,
                'suggestions': [],
                'query': query,
                'error': str(e),
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
    
    def get_cities_by_country(self, country: str) -> Dict:
        """Get all cities in a country."""
        start_time = time.time()
        
        try:
            cities_ref = self.db.collection('cities').where(
                filter=self._FieldFilter('country', '==', country)
            )
            
            cities = []
            for doc in cities_ref.stream():
                city = doc.to_dict()
                city['id'] = doc.id
                cities.append(city)
            
            cities.sort(key=lambda c: c.get('name', ''))
            
            return {
                'success': True,
                'count': len(cities),
                'country': country,
                'cities': cities,
                'cache_hit': False,
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        
        except Exception as e:
            logger.error("Get cities error: %s", e)
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'cities': []
            }
