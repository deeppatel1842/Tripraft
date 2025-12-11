"""
Phase 3: Service Layer Refactoring

Professional service layer for intelligent query detection and search.

Features:
- Intelligent query type detection (country/state/city/place)
- Unified search across all location types
- Search index-based autocomplete
- Caching support (Redis integration)
- Performance tracking and metrics
- Comprehensive error handling and logging
"""

import logging
import time
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import configuration
from ..config import PlacesEngineConfig


class QueryType(Enum):
    """Detected query type"""
    COUNTRY = 'country'
    STATE = 'state'
    CITY = 'city'
    PLACE = 'place'
    UNKNOWN = 'unknown'


@dataclass
class SearchResult:
    """Result of a search query"""
    success: bool
    query: str
    query_type: QueryType
    display_mode: str  # 'country_sections', 'top_destinations', 'single_place'
    
    # Match information
    match_id: Optional[str] = None
    match_name: Optional[str] = None
    location_hierarchy: Optional[Dict[str, str]] = None
    
    # Results
    places: List[Dict] = None
    sections: Optional[List[Dict]] = None  # For country sections
    
    # Metadata
    firestore_reads: int = 0
    response_time_ms: float = 0.0
    cache_hit: bool = False
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.places is None:
            self.places = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'success': self.success,
            'query': self.query,
            'query_type': self.query_type.value,
            'display_mode': self.display_mode,
            'match': {
                'id': self.match_id,
                'name': self.match_name,
                'location_hierarchy': self.location_hierarchy,
            } if self.match_id else None,
            'places': self.places or [],
            'sections': self.sections,
            'firestore_reads': self.firestore_reads,
            'response_time_ms': self.response_time_ms,
            'cache_hit': self.cache_hit,
            'error': self.error,
        }


@dataclass
class AutocompleteResult:
    """Result of autocomplete query"""
    success: bool
    query: str
    suggestions: List[Dict]
    firestore_reads: int = 0
    response_time_ms: float = 0.0
    cache_hit: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'success': self.success,
            'query': self.query,
            'suggestions': self.suggestions,
            'firestore_reads': self.firestore_reads,
            'response_time_ms': self.response_time_ms,
            'cache_hit': self.cache_hit,
            'error': self.error,
        }


class QueryNormalizer:
    """Normalize and clean search queries"""
    
    @staticmethod
    def normalize(query: str) -> str:
        """
        Normalize query to lowercase and remove special characters
        
        Examples:
            "New York" → "new york"
            "Paris, France" → "paris france"
            "Eiffel Tower" → "eiffel tower"
        """
        # Lowercase
        normalized = query.lower().strip()
        
        # Remove special characters except spaces
        normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
        
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    @staticmethod
    def to_slug(text: str) -> str:
        """
        Convert text to slug format for ID lookup
        
        Examples:
            "New York" → "new-york"
            "Eiffel Tower" → "eiffel-tower"
        """
        slug = QueryNormalizer.normalize(text)
        return slug.replace(' ', '-')


class QueryDetector:
    """Detect query type and find matching location"""
    
    def __init__(self, data_store: Optional[Dict] = None):
        """
        Initialize detector with data store
        
        Args:
            data_store: Optional pre-loaded data for testing/caching
        """
        self.data_store = data_store or {}
        self.normalizer = QueryNormalizer()
    
    def detect_type(self, query: str) -> Tuple[QueryType, Optional[str]]:
        """
        Detect query type and find matching ID
        
        Returns:
            (QueryType, matching_id)
        
        Strategy:
            1. Check if it's a country
            2. Check if it's a state
            3. Check if it's a city
            4. Check if it's a place
            5. Return UNKNOWN if no match
        """
        normalized = self.normalizer.normalize(query)
        slug = self.normalizer.to_slug(query)
        
        logger.info(f"Detecting query type for: '{query}' (normalized: '{normalized}')")
        
        # Try to match countries
        countries = self.data_store.get('countries', [])
        for country in countries:
            if self._match_location(query, country):
                logger.info(f"Matched COUNTRY: {country.get('id')}")
                return QueryType.COUNTRY, country.get('id')
        
        # Try to match states
        states = self.data_store.get('states', [])
        for state in states:
            if self._match_location(query, state):
                logger.info(f"Matched STATE: {state.get('id')}")
                return QueryType.STATE, state.get('id')
        
        # Try to match cities
        cities = self.data_store.get('cities', [])
        for city in cities:
            if self._match_location(query, city):
                logger.info(f"Matched CITY: {city.get('id')}")
                return QueryType.CITY, city.get('id')
        
        # Try to match places
        places = self.data_store.get('places', [])
        for place in places:
            if self._match_location(query, place):
                logger.info(f"Matched PLACE: {place.get('id')}")
                return QueryType.PLACE, place.get('id')
        
        logger.info(f"No match found for query: '{query}'")
        return QueryType.UNKNOWN, None
    
    def _match_location(self, query: str, location: Dict) -> bool:
        """
        Check if query matches location
        
        Matching strategy:
            1. Exact match on name (case-insensitive)
            2. Exact match on ID
            3. Exact match on slug
            4. Partial match on name (starts with)
        """
        query_normalized = self.normalizer.normalize(query)
        query_slug = self.normalizer.to_slug(query)
        
        name = location.get('name', '').lower()
        location_id = location.get('id', '').lower()
        
        # Exact match on name
        if name == query_normalized:
            return True
        
        # Exact match on ID
        if location_id == query_slug:
            return True
        
        # Exact match on slug
        location_slug = self.normalizer.to_slug(name)
        if location_slug == query_slug:
            return True
        
        # Partial match (starts with)
        if name.startswith(query_normalized):
            return True
        
        return False


class IntelligentSearchService:
    """
    Professional service layer for intelligent search
    
    Features:
    - Intelligent query type detection
    - Unified search across all location types
    - Result formatting for different display modes
    - Performance tracking
    - Error handling and logging
    """
    
    def __init__(self, data_store: Optional[Dict] = None):
        """
        Initialize IntelligentSearchService
        
        Args:
            data_store: Optional pre-loaded data for development/testing
        """
        self.config = PlacesEngineConfig
        self.data_store = data_store or {}
        self.detector = QueryDetector(self.data_store)
        self.normalizer = QueryNormalizer()
        
        logger.info("IntelligentSearchService initialized")
    
    def intelligent_search(self, query: str, type_override: Optional[str] = None) -> SearchResult:
        """
        Intelligently search across all location types
        
        Args:
            query: User search query
            type_override: Force specific query type (optional)
        
        Returns:
            SearchResult with formatted response
        """
        start_time = time.time()
        firebase_reads = 0
        
        try:
            if not query or not query.strip():
                return SearchResult(
                    success=False,
                    query=query,
                    query_type=QueryType.UNKNOWN,
                    display_mode='error',
                    firestore_reads=firebase_reads,
                    response_time_ms=0,
                    error='Query cannot be empty',
                )
            
            query = query.strip()
            
            # Detect query type
            if type_override:
                try:
                    detected_type = QueryType(type_override)
                    match_id = None
                except ValueError:
                    return SearchResult(
                        success=False,
                        query=query,
                        query_type=QueryType.UNKNOWN,
                        display_mode='error',
                        firestore_reads=firebase_reads,
                        response_time_ms=0,
                        error=f'Invalid type override: {type_override}',
                    )
            else:
                detected_type, match_id = self.detector.detect_type(query)
            
            # Handle country search
            if detected_type == QueryType.COUNTRY:
                firebase_reads += 1
                country = self._get_country(match_id or query)
                
                if country:
                    elapsed = (time.time() - start_time) * 1000
                    return SearchResult(
                        success=True,
                        query=query,
                        query_type=QueryType.COUNTRY,
                        display_mode='country_sections',
                        match_id=country.get('id'),
                        match_name=country.get('name'),
                        location_hierarchy={'country': country.get('name')},
                        places=self._flatten_country_places(country),
                        sections=country.get('states'),
                        firestore_reads=firebase_reads,
                        response_time_ms=elapsed,
                    )
            
            # Handle state search
            elif detected_type == QueryType.STATE:
                firebase_reads += 1
                state = self._get_state(match_id or query)
                
                if state:
                    elapsed = (time.time() - start_time) * 1000
                    return SearchResult(
                        success=True,
                        query=query,
                        query_type=QueryType.STATE,
                        display_mode='top_destinations',
                        match_id=state.get('id'),
                        match_name=state.get('name'),
                        location_hierarchy={
                            'country': state.get('country_name'),
                            'state': state.get('name'),
                        },
                        places=state.get('top_places', []),
                        firestore_reads=firebase_reads,
                        response_time_ms=elapsed,
                    )
            
            # Handle city search
            elif detected_type == QueryType.CITY:
                firebase_reads += 1
                city = self._get_city(match_id or query)
                
                if city:
                    elapsed = (time.time() - start_time) * 1000
                    return SearchResult(
                        success=True,
                        query=query,
                        query_type=QueryType.CITY,
                        display_mode='top_destinations',
                        match_id=city.get('id'),
                        match_name=city.get('name'),
                        location_hierarchy={
                            'country': city.get('country_name'),
                            'state': city.get('state_name'),
                            'city': city.get('name'),
                        },
                        places=city.get('top_places', []),
                        firestore_reads=firebase_reads,
                        response_time_ms=elapsed,
                    )
            
            # Handle place search
            elif detected_type == QueryType.PLACE:
                firebase_reads += 1
                place = self._get_place(match_id or query)
                
                if place:
                    elapsed = (time.time() - start_time) * 1000
                    return SearchResult(
                        success=True,
                        query=query,
                        query_type=QueryType.PLACE,
                        display_mode='single_place',
                        match_id=place.get('id'),
                        match_name=place.get('name'),
                        location_hierarchy={
                            'country': place.get('country'),
                            'state': place.get('state'),
                            'city': place.get('city'),
                        },
                        places=[place],
                        firestore_reads=firebase_reads,
                        response_time_ms=elapsed,
                    )
            
            # Not found
            elapsed = (time.time() - start_time) * 1000
            return SearchResult(
                success=False,
                query=query,
                query_type=detected_type,
                display_mode='error',
                firestore_reads=firebase_reads,
                response_time_ms=elapsed,
                error=f"No results found for '{query}'",
            )
        
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"Error in intelligent_search: {e}", exc_info=True)
            return SearchResult(
                success=False,
                query=query,
                query_type=QueryType.UNKNOWN,
                display_mode='error',
                firestore_reads=firebase_reads,
                response_time_ms=elapsed,
                error=f"Search error: {str(e)}",
            )
    
    def autocomplete(self, query: str, limit: int = 10) -> AutocompleteResult:
        """
        Get autocomplete suggestions
        
        Args:
            query: Search prefix
            limit: Max suggestions to return
        
        Returns:
            AutocompleteResult with suggestions
        """
        start_time = time.time()
        firebase_reads = 0
        
        try:
            if not query or len(query) < 1:
                return AutocompleteResult(
                    success=False,
                    query=query,
                    suggestions=[],
                    firestore_reads=firebase_reads,
                    response_time_ms=0,
                    error='Query too short',
                )
            
            # Normalize query to prefix
            prefix = self.normalizer.normalize(query)[:3].lower()
            
            # Load search index (would be from Firestore in production)
            firebase_reads += 1
            search_index = self._get_search_index(prefix)
            
            if not search_index:
                elapsed = (time.time() - start_time) * 1000
                return AutocompleteResult(
                    success=True,
                    query=query,
                    suggestions=[],
                    firestore_reads=firebase_reads,
                    response_time_ms=elapsed,
                )
            
            # Get suggestions and filter by query
            suggestions = search_index.get('suggestions', [])
            
            # Filter suggestions that match query
            filtered = [
                s for s in suggestions
                if query.lower() in s.get('name', '').lower()
            ]
            
            # Sort by rank and limit
            filtered.sort(key=lambda x: x.get('rank', 0), reverse=True)
            filtered = filtered[:limit]
            
            elapsed = (time.time() - start_time) * 1000
            
            return AutocompleteResult(
                success=True,
                query=query,
                suggestions=filtered,
                firestore_reads=firebase_reads,
                response_time_ms=elapsed,
            )
        
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"Error in autocomplete: {e}", exc_info=True)
            return AutocompleteResult(
                success=False,
                query=query,
                suggestions=[],
                firestore_reads=firebase_reads,
                response_time_ms=elapsed,
                error=f"Autocomplete error: {str(e)}",
            )
    
    # Helper methods for data retrieval
    
    def _get_country(self, query: str) -> Optional[Dict]:
        """Get country by ID or name"""
        countries = self.data_store.get('countries', [])
        slug = self.normalizer.to_slug(query)
        
        for country in countries:
            if country.get('id', '').lower() == slug or country.get('name', '').lower() == query.lower():
                return country
        
        return None
    
    def _get_state(self, query: str) -> Optional[Dict]:
        """Get state by ID or name"""
        states = self.data_store.get('states', [])
        slug = self.normalizer.to_slug(query)
        
        for state in states:
            if state.get('id', '').lower() == slug or state.get('name', '').lower() == query.lower():
                return state
        
        return None
    
    def _get_city(self, query: str) -> Optional[Dict]:
        """Get city by ID or name"""
        cities = self.data_store.get('cities', [])
        slug = self.normalizer.to_slug(query)
        
        for city in cities:
            if city.get('id', '').lower() == slug or city.get('name', '').lower() == query.lower():
                return city
        
        return None
    
    def _get_place(self, query: str) -> Optional[Dict]:
        """Get place by ID or name"""
        places = self.data_store.get('places', [])
        slug = self.normalizer.to_slug(query)
        
        for place in places:
            if place.get('id', '').lower() == slug or place.get('name', '').lower() == query.lower():
                return place
        
        return None
    
    def _get_search_index(self, prefix: str) -> Optional[Dict]:
        """Get search index for prefix"""
        search_index = self.data_store.get('search_index', {})
        return search_index.get(prefix)
    
    def _flatten_country_places(self, country: Dict) -> List[Dict]:
        """Flatten all places from all states in country"""
        all_places = []
        for state in country.get('states', []):
            all_places.extend(state.get('top_places', []))
        return all_places
