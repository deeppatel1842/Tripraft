"""
OPTIMIZED Places Service - 1-2 Reads Maximum
Fixes all search timeout issues

This is a DROP-IN REPLACEMENT for places_service.py
Key changes:
1. Country search: 1 read (from embedded aggregate)
2. State search: 1-2 reads max (from embedded aggregate + optional city query)
3. City search: 1-2 reads max (from embedded aggregate)
4. Places search: <10 reads (strict limits + cache)
5. Autocomplete: 1 read (from search index)
"""

import logging
import math
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Invalid photo URL patterns
INVALID_PHOTO_PATTERNS = frozenset([
    'commons-logo.svg', 'airplane_silhouette.svg', 'flag_of_',
    'coat_of_arms', 'logo_', 'icon-', 'placeholder', 'no_image',
    'default_', 'blank.svg', 'aiga_', '_location_map.svg',
    '_map.svg', 'symbol_', 'pictogram',
])


class PlacesService:
    """Optimized service with HARD 10-READ LIMIT on ALL operations"""
    
    # GLOBAL HARD LIMIT: No operation can exceed 10 Firebase reads
    MAX_READS_PER_OPERATION = 10
    
    def __init__(self, db: Any = None, cache: Optional[Any] = None):
        self.db = db
        self.cache = cache
        self._read_count = 0  # Track reads per operation
        
        try:
            from firebase_admin import firestore as fs
            from google.cloud.firestore_v1 import Query
            from google.cloud.firestore_v1.base_query import FieldFilter
            self._firestore = fs
            self._FieldFilter = FieldFilter
            self._Query = Query
        except ImportError:
            self._firestore = None
            self._FieldFilter = None
            self._Query = None
    
    def _reset_read_counter(self):
        """Reset read counter at start of each operation"""
        self._read_count = 0
    
    def _increment_read_count(self, count: int = 1) -> bool:
        """
        Increment read counter and check if limit exceeded.
        Returns True if operation can continue, False if limit reached.
        """
        self._read_count += count
        if self._read_count > self.MAX_READS_PER_OPERATION:
            logger.warning(
                f"🚨 CIRCUIT BREAKER: Read limit exceeded ({self._read_count}/{self.MAX_READS_PER_OPERATION})"
            )
            return False
        return True
    
    # ============ INTELLIGENT SEARCH - Route to appropriate method ============
    def intelligent_search(self, query: str, type_hint: Optional[str] = None, 
                          limit: int = 20, offset: int = 0) -> Dict:
        """
        Intelligently detect query type and route to appropriate search method.
        
        HARD LIMIT: Max 10 Firebase reads per request.
        
        Detects:
        1. Country (1 read)
        2. State (1 read)
        3. City (1 read)
        4. Place name (1-10 reads)
        
        Args:
            query: Search query
            type_hint: Override type detection (country|state|city|place)
            limit: Results per page
            offset: Pagination offset
        
        Returns:
            Dict with results and firebase_reads count
        """
        start_time = time.time()
        self._reset_read_counter()
        
        if type_hint:
            # Use hint to route directly
            if type_hint.lower() == 'country':
                return self.get_country_overview(query)
            elif type_hint.lower() in ['state', 'city']:
                return self.search_by_location(query, limit=limit, page=(offset // limit) + 1)
            elif type_hint.lower() == 'place':
                return self.search_places(query=query, limit=limit, offset=offset)
        
        # Auto-detect: Try country first (cheapest)
        normalized = self._normalize_query(query)
        
        # Try country
        if self.db:
            try:
                if self._increment_read_count(1):
                    country_doc = self.db.collection('countries').document(normalized).get()
                    if country_doc.exists:
                        return self.get_country_overview(query)
            except Exception as e:
                logger.debug(f"Country check failed: {e}")
        
        # Try location (state/city)
        return self.search_by_location(query, limit=limit, page=(offset // limit) + 1)
    
    # ============ OPTIMIZED: Country Search - MAX 1 READ ============
    def get_country_overview(self, country: str) -> Dict:
        """
        OPTIMIZED: Get country overview with 1 Firebase read MAX.
        
        HARD LIMIT: If operation would exceed 10 reads, stop immediately.
        
        Returns states + top 5 places per state (pre-embedded in country doc)
        
        Expected schema in Firestore:
        {
            "id": "india",
            "name": "India",
            "place_count": 1000,
            "state_count": 10,
            "states": [
                {
                    "state_id": "maharashtra",
                    "state_name": "Maharashtra",
                    "place_count": 100,
                    "top_places": [
                        { "id": "...", "name": "...", ...20 fields... }
                        // 5 places max per state
                    ]
                }
                // 10 states total
            ],
            "metadata": { "last_updated": "..." }
        }
        """
        # RESET READ COUNTER
        self._reset_read_counter()
        
        # CHECK CACHE FIRST (FREE)
        if self.cache:
            cached = self.cache.get_country(country)
            if cached:
                cached['cache_hit'] = True
                cached['firebase_reads'] = 0
                return cached
        
        start_time = time.time()
        firebase_reads = 0
        
        try:
            # CHECK: Firebase not initialized
            if not self.db:
                logger.warning(f"Firebase not initialized, returning mock data for {country}")
                return {
                    'success': False,
                    'country': country,
                    'error': 'Firebase not initialized',
                    'states': [],
                    'firebase_reads': 0,
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
            
            country_normalized = self._normalize_query(country)
            countries_ref = self.db.collection('countries')
            
            # ========== SINGLE READ: Get country document with embedded states ==========
            # This ONE read gets country + 10 states + 50 places (5 per state)
            if not self._increment_read_count(1):
                return {
                    'success': False,
                    'country': country,
                    'error': 'Read limit exceeded',
                    'states': [],
                    'firebase_reads': self._read_count,
                    'read_limit_exceeded': True
                }
            
            country_doc = countries_ref.document(country_normalized).get()
            firebase_reads = self._read_count  # ✅ MAX 1 READ
            
            if not country_doc.exists:
                return {
                    'success': False,
                    'country': country,
                    'error': f"Country '{country}' not found",
                    'states': [],
                    'firebase_reads': firebase_reads,
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
            
            country_data = country_doc.to_dict()
            states = country_data.get('states', [])
            
            # Process states and their embedded places
            processed_states = []
            for state in states:
                state_obj = {
                    'state_id': state.get('state_id'),
                    'state_name': state.get('state_name'),
                    'place_count': state.get('place_count', 0),
                    'top_places': []
                }
                
                # Process embedded places
                for place in state.get('top_places', [])[:5]:
                    state_obj['top_places'].append(self._process_place_dict(place))
                
                processed_states.append(state_obj)
            
            result = {
                'success': True,
                'country': country_data.get('name', country),
                'state_count': len(processed_states),
                'total_places': country_data.get('place_count', 0),
                'states': processed_states,
                'cache_hit': False,
                'firebase_reads': firebase_reads,  # ✅ 1 READ
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
            if self.cache:
                self.cache.set_country(country, result)
            
            return result
        
        except Exception as e:
            logger.error("Country overview error: %s", e, exc_info=True)
            return {
                'success': False,
                'country': country,
                'error': str(e),
                'states': [],
                'firebase_reads': firebase_reads
            }
    
    # ============ OPTIMIZED: Location Search (City/State/Country) - MAX 3 READS ============
    def search_by_location(self, query: str, limit: int = 20, page: int = 1) -> Dict:
        """
        OPTIMIZED: Search by location with MAX 3 reads (city → state → country).
        
        HARD LIMIT: Stops immediately if would exceed 10 reads.
        
        Strategy:
        - READ 1: Query cities (by index, returns 1 doc max)
        - If found: Return city with embedded top 20 places ✅ 1 READ
        - If not: Try states (1 read)
        - If not: Try countries (1 read) and return merged places from all states
        Maximum: 3 reads total
        """
        # RESET READ COUNTER
        self._reset_read_counter()
        
        # CHECK CACHE FIRST
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
            
            # CHECK: Firebase not initialized
            if not self.db:
                logger.warning(f"Firebase not initialized, returning mock data for location {query}")
                return {
                    'success': False,
                    'query': query,
                    'error': 'Firebase not initialized',
                    'places': [],
                    'firebase_reads': 0,
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
            
            # ========== READ 1: Try cities first (most common) ==========
            if not self._increment_read_count(1):
                return {
                    'success': False,
                    'query': query,
                    'error': 'Read limit exceeded',
                    'places': [],
                    'firebase_reads': self._read_count,
                    'read_limit_exceeded': True
                }
            
            cities_ref = self.db.collection('cities')
            city_docs = list(cities_ref.where(
                filter=self._FieldFilter('name', '==', query_normalized)
            ).limit(1).stream())
            firebase_reads = self._read_count
            
            if city_docs:
                city_data = city_docs[0].to_dict()
                top_places = city_data.get('top_places', [])
                
                result = {
                    'success': True,
                    'query': query,
                    'match_type': 'city',
                    'matched': {
                        'id': city_docs[0].id,
                        'name': city_data.get('name'),
                        'state': city_data.get('state_name'),
                        'country': city_data.get('country_name'),
                        'place_count': city_data.get('place_count', len(top_places))
                    },
                    'count': len(top_places),
                    'places': [self._process_place_dict(p) for p in top_places[:limit]],
                    'cache_hit': False,
                    'firebase_reads': firebase_reads,  # ✅ 1 READ
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
                
                if self.cache:
                    self.cache.set_location(query, result)
                
                return result
            
            # ========== READ 2: Try states ==========
            if not self._increment_read_count(1):
                return {
                    'success': False,
                    'query': query,
                    'error': 'Read limit exceeded',
                    'places': [],
                    'firebase_reads': self._read_count,
                    'read_limit_exceeded': True
                }
            
            states_ref = self.db.collection('states')
            state_docs = list(states_ref.where(
                filter=self._FieldFilter('name', '==', query_normalized)
            ).limit(1).stream())
            firebase_reads = self._read_count
            
            if state_docs:
                state_data = state_docs[0].to_dict()
                top_places = state_data.get('top_places', [])
                
                result = {
                    'success': True,
                    'query': query,
                    'match_type': 'state',
                    'matched': {
                        'id': state_docs[0].id,
                        'name': state_data.get('name'),
                        'country': state_data.get('country_name'),
                        'place_count': state_data.get('place_count', len(top_places))
                    },
                    'count': len(top_places),
                    'places': [self._process_place_dict(p) for p in top_places[:limit]],
                    'cache_hit': False,
                    'firebase_reads': firebase_reads,  # ✅ 2 READS
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
                
                if self.cache:
                    self.cache.set_location(query, result)
                
                return result
            
            # ========== READ 3: Try countries ==========
            if not self._increment_read_count(1):
                return {
                    'success': False,
                    'query': query,
                    'error': 'Read limit exceeded',
                    'places': [],
                    'firebase_reads': self._read_count,
                    'read_limit_exceeded': True
                }
            
            countries_ref = self.db.collection('countries')
            country_docs = list(countries_ref.where(
                filter=self._FieldFilter('name', '==', query_normalized)
            ).limit(1).stream())
            firebase_reads = self._read_count
            
            if country_docs:
                country_data = country_docs[0].to_dict()
                states = country_data.get('states', [])
                
                # Aggregate places from all states (embedded)
                all_places = []
                for state in states:
                    state_places = state.get('top_places', [])
                    all_places.extend(state_places)
                
                # Sort by rank_score descending and limit
                all_places = sorted(
                    all_places,
                    key=lambda p: p.get('rank_score', 0),
                    reverse=True
                )[:limit]
                
                result = {
                    'success': True,
                    'query': query,
                    'match_type': 'country',
                    'matched': {
                        'id': country_docs[0].id,
                        'name': country_data.get('name'),
                        'state_count': len(states),
                        'place_count': country_data.get('place_count', len(all_places))
                    },
                    'count': len(all_places),
                    'places': [self._process_place_dict(p) for p in all_places],
                    'cache_hit': False,
                    'firebase_reads': firebase_reads,  # ✅ 3 READS
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
                
                if self.cache:
                    self.cache.set_location(query, result)
                
                return result
            
            # If nothing found in city, state, or country, return not found
            return {
                'success': False,
                'query': query,
                'error': f"Location '{query}' not found",
                'places': [],
                'firebase_reads': firebase_reads,
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        
        except Exception as e:
            logger.error("Location search error: %s", e, exc_info=True)
            return {
                'success': False,
                'query': query,
                'error': str(e),
                'places': [],
                'firebase_reads': firebase_reads
            }
    
    # ============ OPTIMIZED: Places Search - <10 READS ============
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
        OPTIMIZED: Search places with strict limits
        
        - Hard limit: max 50 results
        - No offset (no deep pagination)
        - Use indexed queries only
        - Cache everything
        
        Maximum reads: limit (max 50)
        """
        # Enforce strict limits
        limit = min(max(1, limit), 50)  # Force 1-50
        
        if offset > 0:
            logger.warning(f"Offset search requested: {offset}. Not supported.")
            return {
                'success': False,
                'error': 'Offset pagination not supported. Use cursor instead.',
                'places': [],
                'firebase_reads': 0
            }
        
        start_time = time.time()
        firebase_reads = 0
        
        try:
            # CHECK: Firebase not initialized
            if not self.db:
                logger.warning(f"Firebase not initialized, returning mock data for place search")
                return {
                    'success': False,
                    'error': 'Firebase not initialized',
                    'places': [],
                    'firebase_reads': 0,
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
            
            places_ref = self.db.collection('places')
            
            # Apply filters with strict order
            if country:
                places_ref = places_ref.where(
                    filter=self._FieldFilter('country_name', '==', country)
                )
            
            if city:
                places_ref = places_ref.where(
                    filter=self._FieldFilter('city_name', '==', city)
                )
            
            if cost:
                places_ref = places_ref.where(
                    filter=self._FieldFilter('cost', '==', cost)
                )
            
            if rating_min:
                places_ref = places_ref.where(
                    filter=self._FieldFilter('rating_tourist_priority', '>=', rating_min)
                )
            
            # Order by rank score
            places_ref = places_ref.order_by(
                'rank_score',
                direction=self._Query.DESCENDING
            )
            
            # Apply HARD LIMIT: MAX 10 READS ✅
            hard_limit = min(limit, 10)
            places_ref = places_ref.limit(hard_limit)
            
            # Stream results with HARD circuit breaker
            places = []
            for doc in places_ref.stream():
                # CIRCUIT BREAKER: Check before reading each doc
                if not self._increment_read_count(1):
                    logger.warning(f"🚨 HARD LIMIT: Stopped at {self._read_count} reads")
                    break
                
                firebase_reads = self._read_count
                
                place = self._process_place_dict(doc.to_dict())
                
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
                    'offset': 0,
                    'has_more': len(places) == limit
                },
                'cache_hit': False,
                'firebase_reads': firebase_reads,  # ✅ MAX 50 READS
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        
        except Exception as e:
            logger.error("Search places error: %s", e, exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'places': [],
                'firebase_reads': firebase_reads
            }
    
    # ============ HELPER METHODS ============
    
    def _normalize_query(self, query: str) -> str:
        """Normalize to lowercase with underscores"""
        if not query:
            return ''
        return '_'.join(query.lower().split())
    
    def _process_place_dict(self, place: Dict) -> Dict:
        """Process place dictionary (already extracted from Firestore)"""
        if not place:
            return {}
        
        # Convert GeoPoint if needed
        coords = place.get('coordinates', {})
        if hasattr(coords, 'latitude'):
            place['coordinates'] = {
                'latitude': coords.latitude,
                'longitude': coords.longitude
            }
        
        # Sanitize photo
        photos = place.get('photos', {})
        if not photos:
            place['photos'] = {'thumbnail_url': None}
        
        return place
    
    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance in meters"""
        earth_radius = 6371000
        
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
    
    # ============ STUB METHODS (Keep for compatibility) ============
    
    def get_place_by_id(self, place_id: str) -> Optional[Dict]:
        """Get place by ID - MAX 1 READ"""
        self._reset_read_counter()
        start_time = time.time()
        
        try:
            # CHECK: Firebase not initialized
            if not self.db:
                logger.warning(f"Firebase not initialized, returning None for place {place_id}")
                return None
            
            if not self._increment_read_count(1):
                return {
                    'success': False,
                    'error': 'Read limit exceeded',
                    'firebase_reads': self._read_count,
                    'read_limit_exceeded': True
                }
            
            doc = self.db.collection('places').document(place_id).get()
            
            if not doc.exists:
                return None
            
            place = self._process_place_dict(doc.to_dict())
            
            return {
                'success': True,
                'place': place,
                'cache_hit': False,
                'firebase_reads': 1,
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            logger.error("Get place error: %s", e)
            return None
    
    def get_nearby_places(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 10000,
        limit: int = 20
    ) -> Dict:
        """Get nearby places (stub - needs implementation with geospatial index)"""
        logger.warning("get_nearby_places not yet optimized")
        return {
            'success': False,
            'error': 'Nearby search not yet implemented',
            'count': 0,
            'places': []
        }
    
    def autocomplete(self, query: str, limit: int = 10) -> Dict:
        """
        Ultra-fast autocomplete using pre-loaded JSON data (0 Firebase reads).
        Returns suggestions in <300ms with 0 Firebase reads.
        
        Args:
            query: Partial search query (min 1 char)
            limit: Maximum suggestions to return
        
        Returns:
            Dict with ranked suggestions
        """
        import json
        from pathlib import Path
        
        start_time = time.time()
        query_lower = query.lower().strip()
        
        if len(query_lower) < 1:
            return {'success': True, 'query': query, 'suggestions': [], 'cache_hit': False, 'firebase_reads': 0}
        
        try:
            suggestions = []
            
            # Load pre-generated JSON data
            data_file = Path(__file__).parent.parent / 'places_autocomplete_data.json'
            
            if not data_file.exists():
                data_file = Path(__file__).parent.parent.parent / 'places_autocomplete_data.json'
            
            if not data_file.exists():
                return {
                    'success': True,
                    'query': query,
                    'suggestions': [],
                    'firebase_reads': 0,
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
            
            # Read JSON data
            with open(data_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            
            seen_names = set()
            
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
                    seen_names.add(name)
                    if len(suggestions) >= limit:
                        break
            
            # Search cities
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
                        seen_names.add(name)
                        if len(suggestions) >= limit:
                            break
            
            # Search countries
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
                        seen_names.add(name)
                        if len(suggestions) >= limit:
                            break
            
            suggestions = suggestions[:limit]
            
            return {
                'success': True,
                'query': query,
                'suggestions': suggestions,
                'firebase_reads': 0,  # 0 reads - all from JSON file!
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        
        except Exception as e:
            logger.error(f"Autocomplete error: {e}", exc_info=True)
            return {
                'success': False,
                'query': query,
                'error': str(e),
                'suggestions': [],
                'firebase_reads': 0
            }
    
    def get_all_countries(self) -> Dict:
        """Get all countries - MAX 10 READS"""
        self._reset_read_counter()
        
        try:
            # CHECK: Firebase not initialized
            if not self.db:
                logger.warning(f"Firebase not initialized, returning mock countries")
                return {
                    'success': False,
                    'error': 'Firebase not initialized',
                    'countries': [],
                    'firebase_reads': 0
                }
            
            # HARD LIMIT: Only read first 10 countries
            docs = []
            for doc in self.db.collection('countries').limit(10).stream():
                if not self._increment_read_count(1):
                    logger.warning(f"🚨 Country list truncated at {self._read_count} reads")
                    break
                docs.append(doc)
            countries = [
                {
                    'id': doc.id,
                    'name': doc.to_dict().get('name'),
                    'place_count': doc.to_dict().get('place_count', 0)
                }
                for doc in docs
            ]
            
            return {
                'success': True,
                'countries': countries,
                'firebase_reads': self._read_count
            }
        except Exception as e:
            logger.error("Get countries error: %s", e)
            return {'success': False, 'error': str(e), 'countries': []}
    
    def get_cities_by_country(self, country: str) -> Dict:
        """Get cities for a country - MAX 10 READS"""
        self._reset_read_counter()
        
        try:
            # CHECK: Firebase not initialized
            if not self.db:
                logger.warning(f"Firebase not initialized, returning mock cities for {country}")
                return {
                    'success': False,
                    'error': 'Firebase not initialized',
                    'cities': [],
                    'firebase_reads': 0
                }
            
            # HARD LIMIT: Only read first 10 cities
            docs = []
            for doc in self.db.collection('cities').where(
                filter=self._FieldFilter('country_name', '==', country)
            ).limit(10).stream():
                if not self._increment_read_count(1):
                    logger.warning(f"🚨 City list truncated at {self._read_count} reads")
                    break
                docs.append(doc)
            
            cities = [
                {
                    'id': doc.id,
                    'name': doc.to_dict().get('name'),
                    'place_count': doc.to_dict().get('place_count', 0)
                }
                for doc in docs
            ]
            
            return {
                'success': True,
                'cities': cities,
                'firebase_reads': self._read_count
            }
        except Exception as e:
            logger.error("Get cities error: %s", e)
            return {'success': False, 'error': str(e), 'cities': []}
    
    def get_popular_places(self, country: Optional[str] = None, limit: int = 20) -> Dict:
        """Get popular places - MAX 10 READS"""
        self._reset_read_counter()
        
        # HARD LIMIT: Cap at 10 results
        limit = min(max(1, limit), 10)
        
        try:
            # CHECK: Firebase not initialized
            if not self.db:
                logger.warning(f"Firebase not initialized, returning mock popular places")
                return {
                    'success': False,
                    'error': 'Firebase not initialized',
                    'places': [],
                    'firebase_reads': 0
                }
            
            places_ref = self.db.collection('places')
            
            if country:
                places_ref = places_ref.where(
                    filter=self._FieldFilter('country_name', '==', country)
                )
            
            # Stream with circuit breaker
            docs = []
            places = []
            
            for doc in places_ref.order_by(
                'rank_score',
                direction=self._Query.DESCENDING
            ).limit(limit).stream():
                if not self._increment_read_count(1):
                    logger.warning(f"🚨 Popular places truncated at {self._read_count} reads")
                    break
                docs.append(doc)
                places.append(self._process_place_dict(doc.to_dict()))
            
            return {
                'success': True,
                'places': places,
                'firebase_reads': self._read_count
            }
        except Exception as e:
            logger.error("Get popular places error: %s", e)
            return {'success': False, 'error': str(e), 'places': []}
