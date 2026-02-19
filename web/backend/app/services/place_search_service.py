"""
Place Search Service

Business logic for place search operations.
Handles search, autocomplete, and data retrieval.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import config
from app.domain.places.repository import DatabaseConnection, get_database
from app.domain.places.models import (AutocompleteSuggestion, OpeningHours, Photo,
                                 Place, SearchResult)

logger = logging.getLogger(__name__)


class PlaceSearchService:
    """Service for place search operations"""
    
    def __init__(self, db: Optional[DatabaseConnection] = None):
        """
        Initialize place search service.
        
        Args:
            db: Database connection (uses default if not provided)
        """
        self.db = db or get_database()
    
    def search(
        self,
        query: str,
        limit: int = config.DEFAULT_LIMIT,
        offset: int = 0,
        sort_by: str = config.DEFAULT_SORT_BY,
        sort_order: str = config.DEFAULT_SORT_ORDER,
        cost_filter: Optional[List[str]] = None,
        rating_filter: Optional[int] = None,
    ) -> SearchResult:
        """
        Search for places by query.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Offset for pagination
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            cost_filter: Filter by cost values
            rating_filter: Filter by minimum rating
            
        Returns:
            SearchResult with matching places
        """
        start_time = time.time()
        
        # Validate inputs
        query = query.strip().lower()
        if len(query) < config.MIN_QUERY_LENGTH:
            return SearchResult(
                success=False,
                query=query,
                match_type='none',
                total_count=0,
                places=[],
                response_time_ms=0,
            )
        
        # Validate sort field
        if sort_by not in config.VALID_SORT_FIELDS:
            sort_by = config.DEFAULT_SORT_BY
        
        # Detect search type and get results
        match_type, matched_location, places = self._execute_search(
            query, limit, offset, sort_by, sort_order, cost_filter, rating_filter
        )
        
        response_time = (time.time() - start_time) * 1000
        
        return SearchResult(
            success=True,
            query=query,
            match_type=match_type,
            total_count=len(places),
            places=places,
            matched_location=matched_location,
            response_time_ms=round(response_time, 2),
        )
    
    def _execute_search(
        self,
        query: str,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        cost_filter: Optional[List[str]],
        rating_filter: Optional[int],
    ) -> Tuple[str, Optional[Dict], List[Place]]:
        """
        Execute search and return results.
        
        Logic (priority order):
        - Country: Show top 5 places per state
        - City: If >30 places, show top 30; else show all places
        - State: If >30 places, show top 5 per city; else show all places
        - Place: Show matching places
        
        Note: City is checked BEFORE state to handle cases like "Jaipur"
        which exists as both a city and state.
        
        Returns:
            Tuple of (match_type, matched_location, places)
        """
        # Try matching country first
        country = self._find_country(query)
        if country:
            places = self._get_places_by_country(
                country['id'], limit, offset, sort_by, sort_order, 
                cost_filter, rating_filter
            )
            return 'country', country, places
        
        # Try matching city BEFORE state (cities are more specific)
        city = self._find_city(query)
        if city:
            # Check count first
            count = self._count_places_by_city(city['id'])
            if count > 30:
                # More than 30 places: show top 30 ranked
                places = self._get_places_by_city(
                    city['id'], 30, 0, sort_by, sort_order,
                    cost_filter, rating_filter
                )
            else:
                # 30 or fewer: show all places
                places = self._get_places_by_city(
                    city['id'], 500, offset, sort_by, sort_order,
                    cost_filter, rating_filter
                )
            return 'city', city, places
        
        # Try matching state
        state = self._find_state(query)
        if state:
            # Check count first
            count = self._count_places_by_state(state['id'])
            if count > 30:
                # More than 30 places: show top 5 per city (like country)
                places = self._get_places_by_state(
                    state['id'], limit, offset, sort_by, sort_order,
                    cost_filter, rating_filter
                )
            else:
                # 30 or fewer: show all places
                places = self._get_all_places_by_state(
                    state['id'], sort_by, sort_order,
                    cost_filter, rating_filter
                )
            return 'state', state, places
        
        # Search places directly (single place search)
        places = self._search_places(
            query, limit, offset, sort_by, sort_order,
            cost_filter, rating_filter
        )
        return 'place', None, places
    
    def _find_country(self, query: str) -> Optional[Dict]:
        """Find country by name"""
        sql = """
            SELECT id, country_name 
            FROM countries 
            WHERE LOWER(country_name) LIKE ?
            LIMIT 1
        """
        return self.db.execute_single(sql, (f'%{query}%',))
    
    def _find_state(self, query: str) -> Optional[Dict]:
        """Find state by name"""
        sql = """
            SELECT s.id, s.state_name, c.country_name
            FROM states s
            JOIN countries c ON s.country_id = c.id
            WHERE LOWER(s.state_name) LIKE ?
            LIMIT 1
        """
        return self.db.execute_single(sql, (f'%{query}%',))
    
    def _find_city(self, query: str) -> Optional[Dict]:
        """Find city by name"""
        sql = """
            SELECT ci.id, ci.city_name, s.state_name, c.country_name
            FROM cities ci
            JOIN states s ON ci.state_id = s.id
            JOIN countries c ON s.country_id = c.id
            WHERE LOWER(ci.city_name) LIKE ?
            LIMIT 1
        """
        return self.db.execute_single(sql, (f'%{query}%',))
    
    def _count_places_by_state(self, state_id: int) -> int:
        """Count total places in a state"""
        sql = """
            SELECT COUNT(*) as count
            FROM places p
            JOIN cities ci ON p.city_id = ci.id
            WHERE ci.state_id = ?
        """
        result = self.db.execute_single(sql, (state_id,))
        return result['count'] if result else 0
    
    def _count_places_by_city(self, city_id: int) -> int:
        """Count total places in a city"""
        sql = """
            SELECT COUNT(*) as count
            FROM places p
            WHERE p.city_id = ?
        """
        result = self.db.execute_single(sql, (city_id,))
        return result['count'] if result else 0
    
    def _get_all_places_by_state(
        self, state_id: int, sort_by: str, sort_order: str,
        cost_filter: Optional[List[str]], rating_filter: Optional[int]
    ) -> List[Place]:
        """
        Get all places for a state (when count <= 30).
        No grouping, returns all places sorted.
        """
        order_dir = "DESC" if sort_order.lower() == 'desc' else "ASC"
        
        filters = ["ci.state_id = ?"]
        params = [state_id]
        
        if cost_filter:
            placeholders = ','.join('?' * len(cost_filter))
            filters.append(f"p.cost IN ({placeholders})")
            params.extend(cost_filter)
        
        if rating_filter:
            filters.append("p.rating_tourist_priority >= ?")
            params.append(rating_filter)
        
        where_clause = " AND ".join(filters)
        
        sql = f"""
            SELECT 
                p.*,
                ci.city_name,
                s.state_name,
                c.country_name,
                ph.thumbnail_url as photo_url
            FROM places p
            JOIN cities ci ON p.city_id = ci.id
            JOIN states s ON ci.state_id = s.id
            JOIN countries c ON s.country_id = c.id
            LEFT JOIN photos ph ON p.id = ph.place_id
            WHERE {where_clause}
            ORDER BY p.{sort_by} {order_dir}
        """
        return self._fetch_places(sql, tuple(params))

    def _get_places_by_country(
        self, country_id: int, limit: int, offset: int,
        sort_by: str, sort_order: str,
        cost_filter: Optional[List[str]], rating_filter: Optional[int]
    ) -> List[Place]:
        """
        Get top 5 places per state for a country.
        Groups results by state and returns top 5 places from each.
        No limit applied - returns all states for the country.
        """
        order_dir = "DESC" if sort_order.lower() == 'desc' else "ASC"
        
        # Get top 5 places per state using ROW_NUMBER() window function
        # No LIMIT to ensure all states are returned
        sql = f"""
            WITH RankedPlaces AS (
                SELECT 
                    p.*,
                    ci.city_name,
                    s.state_name,
                    c.country_name,
                    ph.thumbnail_url as photo_url,
                    ROW_NUMBER() OVER (
                        PARTITION BY s.id 
                        ORDER BY p.rank_score DESC
                    ) as state_rank
                FROM places p
                JOIN cities ci ON p.city_id = ci.id
                JOIN states s ON ci.state_id = s.id
                JOIN countries c ON s.country_id = c.id
                LEFT JOIN photos ph ON p.id = ph.place_id
                WHERE c.id = ?
            )
            SELECT * FROM RankedPlaces 
            WHERE state_rank <= 5
            ORDER BY state_name, rank_score {order_dir}
        """
        return self._fetch_places(sql, (country_id,))
    
    def _get_places_by_state(
        self, state_id: int, limit: int, offset: int,
        sort_by: str, sort_order: str,
        cost_filter: Optional[List[str]], rating_filter: Optional[int]
    ) -> List[Place]:
        """
        Get top 5 places per city for a state.
        Groups results by city and returns top 5 places from each.
        No limit applied - returns all cities for the state.
        """
        order_dir = "DESC" if sort_order.lower() == 'desc' else "ASC"
        
        # Get top 5 places per city using ROW_NUMBER() window function
        # No LIMIT to ensure all cities are returned
        sql = f"""
            WITH RankedPlaces AS (
                SELECT 
                    p.*,
                    ci.city_name,
                    s.state_name,
                    c.country_name,
                    ph.thumbnail_url as photo_url,
                    ROW_NUMBER() OVER (
                        PARTITION BY ci.id 
                        ORDER BY p.rank_score DESC
                    ) as city_rank
                FROM places p
                JOIN cities ci ON p.city_id = ci.id
                JOIN states s ON ci.state_id = s.id
                JOIN countries c ON s.country_id = c.id
                LEFT JOIN photos ph ON p.id = ph.place_id
                WHERE s.id = ?
            )
            SELECT * FROM RankedPlaces 
            WHERE city_rank <= 5
            ORDER BY city_name, rank_score {order_dir}
        """
        return self._fetch_places(sql, (state_id,))
    
    def _get_places_by_city(
        self, city_id: int, limit: int, offset: int,
        sort_by: str, sort_order: str,
        cost_filter: Optional[List[str]], rating_filter: Optional[int]
    ) -> List[Place]:
        """
        Get ALL places for a city.
        When a city is selected, show all places without grouping.
        """
        order_dir = "DESC" if sort_order.lower() == 'desc' else "ASC"
        
        filters = ["p.city_id = ?"]
        params = [city_id]
        
        if cost_filter:
            placeholders = ','.join('?' * len(cost_filter))
            filters.append(f"p.cost IN ({placeholders})")
            params.extend(cost_filter)
        
        if rating_filter:
            filters.append("p.rating_tourist_priority >= ?")
            params.append(rating_filter)
        
        where_clause = " AND ".join(filters)
        
        sql = f"""
            SELECT 
                p.*,
                ci.city_name,
                s.state_name,
                c.country_name,
                ph.thumbnail_url as photo_url
            FROM places p
            JOIN cities ci ON p.city_id = ci.id
            JOIN states s ON ci.state_id = s.id
            JOIN countries c ON s.country_id = c.id
            LEFT JOIN photos ph ON p.id = ph.place_id
            WHERE {where_clause}
            ORDER BY p.{sort_by} {order_dir}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self._fetch_places(sql, tuple(params))
    
    def _search_places(
        self, query: str, limit: int, offset: int,
        sort_by: str, sort_order: str,
        cost_filter: Optional[List[str]], rating_filter: Optional[int]
    ) -> List[Place]:
        """Search places by name"""
        filters = []
        params = []
        
        filters.append("LOWER(p.place_name) LIKE ?")
        params.append(f'%{query}%')
        
        if cost_filter:
            placeholders = ','.join('?' * len(cost_filter))
            filters.append(f"p.cost IN ({placeholders})")
            params.extend(cost_filter)
        
        if rating_filter:
            filters.append("p.rating_tourist_priority >= ?")
            params.append(rating_filter)
        
        where_clause = " AND ".join(filters)
        order_dir = "DESC" if sort_order.lower() == 'desc' else "ASC"
        
        sql = f"""
            SELECT 
                p.*,
                ci.city_name,
                s.state_name,
                c.country_name,
                ph.thumbnail_url as photo_url
            FROM places p
            JOIN cities ci ON p.city_id = ci.id
            JOIN states s ON ci.state_id = s.id
            JOIN countries c ON s.country_id = c.id
            LEFT JOIN photos ph ON p.id = ph.place_id
            WHERE {where_clause}
            ORDER BY p.{sort_by} {order_dir}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        return self._fetch_places(sql, tuple(params))
    
    def _build_places_query(
        self, filter_field: str, filter_value: int,
        limit: int, offset: int, sort_by: str, sort_order: str,
        cost_filter: Optional[List[str]], rating_filter: Optional[int]
    ) -> Tuple[str, tuple]:
        """Build SQL query for fetching places"""
        filters = []
        params = []
        
        # Add location filter based on hierarchy
        if filter_field == 'country_id':
            filters.append("c.id = ?")
        elif filter_field == 'state_id':
            filters.append("s.id = ?")
        else:
            filters.append("p.city_id = ?")
        params.append(filter_value)
        
        if cost_filter:
            placeholders = ','.join('?' * len(cost_filter))
            filters.append(f"p.cost IN ({placeholders})")
            params.extend(cost_filter)
        
        if rating_filter:
            filters.append("p.rating_tourist_priority >= ?")
            params.append(rating_filter)
        
        where_clause = " AND ".join(filters)
        order_dir = "DESC" if sort_order.lower() == 'desc' else "ASC"
        
        sql = f"""
            SELECT 
                p.*,
                ci.city_name,
                c.country_name,
                ph.thumbnail_url as photo_url
            FROM places p
            JOIN cities ci ON p.city_id = ci.id
            JOIN states s ON ci.state_id = s.id
            JOIN countries c ON s.country_id = c.id
            LEFT JOIN photos ph ON p.id = ph.place_id
            WHERE {where_clause}
            ORDER BY p.{sort_by} {order_dir}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        return sql, tuple(params)
    
    def _fetch_places(self, sql: str, params: tuple) -> List[Place]:
        """Fetch and convert places from database"""
        rows = self.db.execute_query(sql, params)
        places = []
        
        for row in rows:
            place = Place(
                id=row['id'],
                city_id=row['city_id'],
                place_name=row['place_name'],
                name_english=row.get('name_english'),
                ai_summary=row.get('ai_summary'),
                suggested_duration=row.get('suggested_duration'),
                best_time_to_visit=row.get('best_time_to_visit'),
                place_tip=row.get('place_tip'),
                advanced_booking=row.get('advanced_booking'),
                state_name=row.get('state_name'),
                sunrise_view=bool(row.get('sunrise_view')),
                sunset_view=bool(row.get('sunset_view')),
                sunrise_time=row.get('sunrise_time'),
                sunset_time=row.get('sunset_time'),
                cost=row.get('cost'),
                rating_tourist_priority=row.get('rating_tourist_priority'),
                rating_traveler_experience=row.get('rating_traveler_experience'),
                latitude=row.get('latitude'),
                longitude=row.get('longitude'),
                address=row.get('address'),
                official_website=row.get('official_website'),
                rank_score=row.get('rank_score'),
                city_name=row.get('city_name'),
                country_name=row.get('country_name'),
            )
            
            # Add photo if available
            if row.get('photo_url'):
                place.photo = Photo(
                    id=0,
                    place_id=place.id,
                    thumbnail_url=row['photo_url']
                )
            
            # Fetch tags
            place.tags = self._get_place_tags(place.id)
            
            # Fetch opening hours
            place.opening_hours = self._get_opening_hours(place.id)
            
            places.append(place)
        
        return places
    
    def _get_opening_hours(self, place_id: int) -> Optional[OpeningHours]:
        """Get opening hours for a place"""
        sql = """
            SELECT *
            FROM opening_hours
            WHERE place_id = ?
            LIMIT 1
        """
        row = self.db.execute_single(sql, (place_id,))
        if row:
            return OpeningHours(
                id=row.get('id', 0),
                place_id=place_id,
                monday=row.get('monday'),
                tuesday=row.get('tuesday'),
                wednesday=row.get('wednesday'),
                thursday=row.get('thursday'),
                friday=row.get('friday'),
                saturday=row.get('saturday'),
                sunday=row.get('sunday'),
                notes=row.get('notes'),
            )
        return None
    
    def _get_place_tags(self, place_id: int) -> List[str]:
        """Get tags for a place"""
        sql = """
            SELECT t.tag_name
            FROM tags t
            JOIN place_tags pt ON t.id = pt.tag_id
            WHERE pt.place_id = ?
            LIMIT 10
        """
        rows = self.db.execute_query(sql, (place_id,))
        return [row['tag_name'] for row in rows]
    
    def get_autocomplete(
        self, 
        query: str, 
        limit: int = config.AUTOCOMPLETE_MAX_RESULTS
    ) -> List[AutocompleteSuggestion]:
        """
        Get autocomplete suggestions.
        
        Args:
            query: Partial search query
            limit: Maximum number of suggestions
            
        Returns:
            List of autocomplete suggestions
        """
        if len(query) < config.AUTOCOMPLETE_MIN_LENGTH:
            return []
        
        query = query.strip().lower()
        all_suggestions = []
        
        # Get country suggestions
        country_suggestions = self._get_country_suggestions(query, 3)
        all_suggestions.extend(country_suggestions)
        
        # Get city suggestions (prioritize over state)
        city_suggestions = self._get_city_suggestions(query, 5)
        all_suggestions.extend(city_suggestions)
        
        # Get state suggestions
        state_suggestions = self._get_state_suggestions(query, 3)
        all_suggestions.extend(state_suggestions)
        
        # Get place suggestions
        place_suggestions = self._get_place_suggestions(query, 5)
        all_suggestions.extend(place_suggestions)
        
        # Deduplicate by name (case-insensitive)
        # Priority: city > state > country > place (city added first)
        seen_names = set()
        unique_suggestions = []
        for s in all_suggestions:
            name_key = s.name.lower().strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_suggestions.append(s)
        
        return unique_suggestions[:limit]
    
    def _get_country_suggestions(
        self, query: str, limit: int
    ) -> List[AutocompleteSuggestion]:
        """Get country autocomplete suggestions"""
        sql = """
            SELECT id, country_name 
            FROM countries 
            WHERE LOWER(country_name) LIKE ?
            LIMIT ?
        """
        rows = self.db.execute_query(sql, (f'%{query}%', limit))
        return [
            AutocompleteSuggestion(
                id=f"c{row['id']}",
                name=row['country_name'],
                type='country',
                parent=None
            )
            for row in rows
        ]
    
    def _get_state_suggestions(
        self, query: str, limit: int
    ) -> List[AutocompleteSuggestion]:
        """Get state autocomplete suggestions"""
        sql = """
            SELECT s.id, s.state_name, c.country_name
            FROM states s
            JOIN countries c ON s.country_id = c.id
            WHERE LOWER(s.state_name) LIKE ?
            LIMIT ?
        """
        rows = self.db.execute_query(sql, (f'%{query}%', limit))
        return [
            AutocompleteSuggestion(
                id=f"s{row['id']}",
                name=row['state_name'],
                type='state',
                parent=row['country_name']
            )
            for row in rows
        ]
    
    def _get_city_suggestions(
        self, query: str, limit: int
    ) -> List[AutocompleteSuggestion]:
        """Get city autocomplete suggestions"""
        sql = """
            SELECT ci.id, ci.city_name, s.state_name, c.country_name
            FROM cities ci
            JOIN states s ON ci.state_id = s.id
            JOIN countries c ON s.country_id = c.id
            WHERE LOWER(ci.city_name) LIKE ?
            LIMIT ?
        """
        rows = self.db.execute_query(sql, (f'%{query}%', limit))
        return [
            AutocompleteSuggestion(
                id=f"city{row['id']}",
                name=row['city_name'],
                type='city',
                parent=f"{row['state_name']}, {row['country_name']}"
            )
            for row in rows
        ]
    
    def _get_place_suggestions(
        self, query: str, limit: int
    ) -> List[AutocompleteSuggestion]:
        """Get place autocomplete suggestions"""
        sql = """
            SELECT p.id, p.place_name, ci.city_name, c.country_name
            FROM places p
            JOIN cities ci ON p.city_id = ci.id
            JOIN states s ON ci.state_id = s.id
            JOIN countries c ON s.country_id = c.id
            WHERE LOWER(p.place_name) LIKE ?
            ORDER BY p.rank_score DESC
            LIMIT ?
        """
        rows = self.db.execute_query(sql, (f'%{query}%', limit))
        return [
            AutocompleteSuggestion(
                id=f"p{row['id']}",
                name=row['place_name'],
                type='place',
                parent=f"{row['city_name']}, {row['country_name']}"
            )
            for row in rows
        ]
    
    def get_place_by_id(self, place_id: int) -> Optional[Place]:
        """
        Get a single place by ID with full details.
        
        Args:
            place_id: Place ID
            
        Returns:
            Place with full details or None
        """
        sql = """
            SELECT 
                p.*,
                ci.city_name,
                c.country_name,
                ph.thumbnail_url as photo_url
            FROM places p
            JOIN cities ci ON p.city_id = ci.id
            JOIN states s ON ci.state_id = s.id
            JOIN countries c ON s.country_id = c.id
            LEFT JOIN photos ph ON p.id = ph.place_id
            WHERE p.id = ?
        """
        places = self._fetch_places(sql, (place_id,))
        
        if not places:
            return None
        
        place = places[0]
        
        # Fetch opening hours
        hours_sql = """
            SELECT * FROM opening_hours WHERE place_id = ?
        """
        hours_row = self.db.execute_single(hours_sql, (place_id,))
        if hours_row:
            place.opening_hours = OpeningHours(**hours_row)
        
        return place
