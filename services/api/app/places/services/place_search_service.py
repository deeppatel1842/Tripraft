# Purpose: Place Search Service Business logic for place search operations.
"""
Place Search Service

Business logic for place search operations.
Handles search, autocomplete, and data retrieval.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

from app.core.config import Config, config
from app.places.models import (AutocompleteSuggestion, OpeningHours,
                                      Photo, Place, SearchResult)
from app.places.repository import DatabaseConnection, get_database

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
        
        Handles comma-separated destination strings like "Seattle, Washington, USA"
        by trying the full query first, then individual components.
        
        Returns:
            Tuple of (match_type, matched_location, places)
        """
        # Comma-separated destinations (e.g. "Seattle, Washington, USA"):
        # split and try each component through the full cascade.
        # The first part is typically the most specific (city name).
        if ',' in query:
            parts = [p.strip() for p in query.split(',') if p.strip()]
            for part in parts:
                result = self._try_search(
                    part, limit, offset, sort_by, sort_order, cost_filter, rating_filter
                )
                if result:
                    return result

        # Single-term query or comma-split found nothing - try the raw query
        result = self._try_search(
            query, limit, offset, sort_by, sort_order, cost_filter, rating_filter
        )
        if result:
            return result

        # Nothing matched anywhere - return empty
        return 'place', None, []

    def _try_search(
        self,
        query: str,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        cost_filter: Optional[List[str]],
        rating_filter: Optional[int],
    ) -> Optional[Tuple[str, Optional[Dict], List[Place]]]:
        """
        Attempt a single search pass against the cascade:
        country -> city -> state -> place name.
        
        Returns the match tuple if something is found, None otherwise.
        """
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
            if count > Config.PLACES_COUNT_THRESHOLD:
                # More than threshold: show top ranked
                places = self._get_places_by_city(
                    city['id'], Config.PLACES_COUNT_THRESHOLD, 0, sort_by, sort_order,
                    cost_filter, rating_filter
                )
            else:
                # Under threshold: show all places
                places = self._get_places_by_city(
                    city['id'], Config.PLACES_CITY_LIMIT, offset, sort_by, sort_order,
                    cost_filter, rating_filter
                )
            return 'city', city, places
        
        # Try matching state
        state = self._find_state(query)
        if state:
            # Check count first
            count = self._count_places_by_state(state['id'])
            if count > Config.PLACES_COUNT_THRESHOLD:
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
        if places:
            return 'place', None, places
        
        return None
    
    def _find_country(self, query: str) -> Optional[Dict]:
        """Find country by name using NOCASE index."""
        sql = """
            SELECT id, country_name 
            FROM countries 
            WHERE country_name LIKE ? COLLATE NOCASE
            LIMIT 1
        """
        return self.db.execute_single(sql, (f'%{query}%',))
    
    def _find_state(self, query: str) -> Optional[Dict]:
        """Find state by name using NOCASE index."""
        sql = """
            SELECT s.id, s.state_name, c.country_name
            FROM states s
            JOIN countries c ON s.country_id = c.id
            WHERE s.state_name LIKE ? COLLATE NOCASE
            LIMIT 1
        """
        return self.db.execute_single(sql, (f'%{query}%',))
    
    def _find_city(self, query: str) -> Optional[Dict]:
        """Find city by name using NOCASE index."""
        sql = """
            SELECT ci.id, ci.city_name, s.state_name, c.country_name
            FROM cities ci
            JOIN states s ON ci.state_id = s.id
            JOIN countries c ON s.country_id = c.id
            WHERE ci.city_name LIKE ? COLLATE NOCASE
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
        Filters are pushed into the CTE to avoid ranking discarded rows.
        """
        order_dir = "DESC" if sort_order.lower() == 'desc' else "ASC"

        filters = ["c.id = ?"]
        params: list = [country_id]

        if cost_filter:
            placeholders = ','.join('?' * len(cost_filter))
            filters.append(f"p.cost IN ({placeholders})")
            params.extend(cost_filter)
        if rating_filter:
            filters.append("p.rating_tourist_priority >= ?")
            params.append(rating_filter)

        where_clause = " AND ".join(filters)

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
                WHERE {where_clause}
            )
            SELECT * FROM RankedPlaces 
            WHERE state_rank <= 5
            ORDER BY state_name, rank_score {order_dir}
        """
        return self._fetch_places(sql, tuple(params))
    
    def _get_places_by_state(
        self, state_id: int, limit: int, offset: int,
        sort_by: str, sort_order: str,
        cost_filter: Optional[List[str]], rating_filter: Optional[int]
    ) -> List[Place]:
        """
        Get top 5 places per city for a state.
        Groups results by city and returns top 5 places from each.
        Filters are pushed into the CTE to avoid ranking discarded rows.
        """
        order_dir = "DESC" if sort_order.lower() == 'desc' else "ASC"

        filters = ["s.id = ?"]
        params: list = [state_id]

        if cost_filter:
            placeholders = ','.join('?' * len(cost_filter))
            filters.append(f"p.cost IN ({placeholders})")
            params.extend(cost_filter)
        if rating_filter:
            filters.append("p.rating_tourist_priority >= ?")
            params.append(rating_filter)

        where_clause = " AND ".join(filters)

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
                WHERE {where_clause}
            )
            SELECT * FROM RankedPlaces 
            WHERE city_rank <= 5
            ORDER BY city_name, rank_score {order_dir}
        """
        return self._fetch_places(sql, tuple(params))
    
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
        """Search places by name using FTS5 with LIKE fallback."""
        order_dir = "DESC" if sort_order.lower() == 'desc' else "ASC"

        # Build FTS5 match term (prefix search)
        # Strip quotes and commas — commas cause FTS5 syntax errors
        fts_term = query.replace('"', '').replace("'", '').replace(',', ' ')
        fts_term = ' '.join(fts_term.split())  # collapse whitespace
        fts_match = f'"{fts_term}" OR {fts_term}*' if len(fts_term) >= 2 else f'"{fts_term}"'

        # Extra filters for cost/rating
        extra_filters = []
        extra_params = []
        if cost_filter:
            placeholders = ','.join('?' * len(cost_filter))
            extra_filters.append(f"p.cost IN ({placeholders})")
            extra_params.extend(cost_filter)
        if rating_filter:
            extra_filters.append("p.rating_tourist_priority >= ?")
            extra_params.append(rating_filter)

        extra_where = (" AND " + " AND ".join(extra_filters)) if extra_filters else ""

        # FTS5 query — search across place_name and name_english columns
        sql = f"""
            SELECT 
                p.*,
                ci.city_name,
                s.state_name,
                c.country_name,
                ph.thumbnail_url as photo_url
            FROM places_fts fts
            JOIN places p ON p.id = fts.rowid
            JOIN cities ci ON p.city_id = ci.id
            JOIN states s ON ci.state_id = s.id
            JOIN countries c ON s.country_id = c.id
            LEFT JOIN photos ph ON p.id = ph.place_id
            WHERE places_fts MATCH ?{extra_where}
            ORDER BY p.{sort_by} {order_dir}
            LIMIT ? OFFSET ?
        """
        params = [fts_match] + extra_params + [limit, offset]

        try:
            results = self._fetch_places(sql, tuple(params))
            if results:
                return results
        except Exception:
            logger.debug("FTS5 search failed for '%s', falling back to LIKE", query)

        # Fallback to LIKE if FTS5 returns nothing or errors
        filters = ["p.place_name LIKE ? COLLATE NOCASE"]
        params = [f'%{query}%']
        params.extend(extra_params)
        if extra_filters:
            filters.extend(extra_filters)

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
        
        return sql, tuple(params)
    
    def _fetch_places(self, sql: str, params: tuple) -> List[Place]:
        """Fetch and convert places from database (batched tags + hours)."""
        rows = self.db.execute_query(sql, params)
        if not rows:
            return []

        places = []
        place_ids = []

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

            if row.get('photo_url'):
                place.photo = Photo(
                    id=0,
                    place_id=place.id,
                    thumbnail_url=row['photo_url']
                )

            places.append(place)
            place_ids.append(place.id)

        # Batch fetch tags for all places (single query instead of N)
        tags_by_place = self._get_tags_batch(place_ids)
        hours_by_place = self._get_hours_batch(place_ids)

        for place in places:
            place.tags = tags_by_place.get(place.id, [])
            place.opening_hours = hours_by_place.get(place.id)

        return places

    def _get_tags_batch(self, place_ids: List[int]) -> Dict[int, List[str]]:
        """Batch fetch tags for multiple places in a single query."""
        if not place_ids:
            return {}
        placeholders = ','.join('?' * len(place_ids))
        sql = f"""
            SELECT pt.place_id, t.tag_name
            FROM tags t
            JOIN place_tags pt ON t.id = pt.tag_id
            WHERE pt.place_id IN ({placeholders})
        """
        rows = self.db.execute_query(sql, tuple(place_ids))
        result: Dict[int, List[str]] = {}
        for row in rows:
            result.setdefault(row['place_id'], []).append(row['tag_name'])
        return result

    def _get_hours_batch(self, place_ids: List[int]) -> Dict[int, OpeningHours]:
        """Batch fetch opening hours for multiple places in a single query."""
        if not place_ids:
            return {}
        placeholders = ','.join('?' * len(place_ids))
        sql = f"""
            SELECT *
            FROM opening_hours
            WHERE place_id IN ({placeholders})
        """
        rows = self.db.execute_query(sql, tuple(place_ids))
        result: Dict[int, OpeningHours] = {}
        for row in rows:
            pid = row['place_id']
            if pid not in result:  # keep first row per place
                result[pid] = OpeningHours(
                    id=row.get('id', 0),
                    place_id=pid,
                    monday=row.get('monday'),
                    tuesday=row.get('tuesday'),
                    wednesday=row.get('wednesday'),
                    thursday=row.get('thursday'),
                    friday=row.get('friday'),
                    saturday=row.get('saturday'),
                    sunday=row.get('sunday'),
                    notes=row.get('notes'),
                )
        return result
    
    def get_autocomplete(
        self, 
        query: str, 
        limit: int = config.AUTOCOMPLETE_MAX_RESULTS
    ) -> List[AutocompleteSuggestion]:
        """Get autocomplete suggestions using a single UNION query."""
        if len(query) < config.AUTOCOMPLETE_MIN_LENGTH:
            return []
        
        query = query.strip().lower()
        like_pattern = f'%{query}%'
        
        # Single UNION query replaces 4 separate full-table scans
        sql = """
            SELECT * FROM (
                SELECT 'country' as type, 'c' || id as suggestion_id,
                       country_name as name, NULL as parent, 0 as score
                FROM countries
                WHERE country_name LIKE ? COLLATE NOCASE
                LIMIT 3
            )

            UNION ALL

            SELECT * FROM (
                SELECT 'city' as type, 'city' || ci.id as suggestion_id,
                       ci.city_name as name,
                       s.state_name || ', ' || c.country_name as parent, 1 as score
                FROM cities ci
                JOIN states s ON ci.state_id = s.id
                JOIN countries c ON s.country_id = c.id
                WHERE ci.city_name LIKE ? COLLATE NOCASE
                LIMIT 5
            )

            UNION ALL

            SELECT * FROM (
                SELECT 'state' as type, 's' || s.id as suggestion_id,
                       s.state_name as name,
                       c.country_name as parent, 2 as score
                FROM states s
                JOIN countries c ON s.country_id = c.id
                WHERE s.state_name LIKE ? COLLATE NOCASE
                LIMIT 3
            )

            UNION ALL

            SELECT * FROM (
                SELECT 'place' as type, 'p' || p.id as suggestion_id,
                       p.place_name as name,
                       ci.city_name || ', ' || c.country_name as parent,
                       3 as score
                FROM places p
                JOIN cities ci ON p.city_id = ci.id
                JOIN states s ON ci.state_id = s.id
                JOIN countries c ON s.country_id = c.id
                WHERE p.place_name LIKE ? COLLATE NOCASE
                ORDER BY p.rank_score DESC
                LIMIT 5
            )
        """
        
        rows = self.db.execute_query(
            sql, (like_pattern, like_pattern, like_pattern, like_pattern)
        )
        
        # Deduplicate by name, preserve priority order (country/city first)
        seen_names = set()
        suggestions = []
        for row in rows:
            name_key = row['name'].lower().strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                suggestions.append(AutocompleteSuggestion(
                    id=row['suggestion_id'],
                    name=row['name'],
                    type=row['type'],
                    parent=row['parent'],
                ))
        
        return suggestions[:limit]
    
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
        
        # Fetch all photos for the gallery
        photos_sql = """
            SELECT * FROM photos WHERE place_id = ?
        """
        photo_rows = self.db.execute_query(photos_sql, (place_id,))
        place.photos = [Photo(**row) for row in photo_rows]

        # Fetch opening hours
        hours_sql = """
            SELECT * FROM opening_hours WHERE place_id = ?
        """
        hours_row = self.db.execute_single(hours_sql, (place_id,))
        if hours_row:
            place.opening_hours = OpeningHours(**hours_row)
        
        return place
