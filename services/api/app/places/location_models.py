# Purpose: Data models for places API Provides query methods for places, cities, states, and countries.
"""
Data models for places API
Provides query methods for places, cities, states, and countries.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from app.core.apiutils.database import get_db

logger = logging.getLogger(__name__)


def parse_json_field(value: Any) -> Any:
    """
    Parse JSON string fields to Python objects
    
    Args:
        value: Field value (string or already parsed)
        
    Returns:
        Parsed Python object or original value
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def transform_place_row(place: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a place row from database, parsing JSON fields
    
    Args:
        place: Raw place dictionary from database
        
    Returns:
        Transformed place with parsed JSON fields
    """
    if not place:
        return place
    
    # Parse JSON fields
    json_fields = ['photos', 'coordinates', 'tags', 'opening_hours']
    for field in json_fields:
        if field in place and place[field]:
            place[field] = parse_json_field(place[field])
    
    return place


class PlacesModel:
    """Model for places data operations"""
    
    @staticmethod
    def get_by_id(place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single place by ID
        
        Args:
            place_id: Place identifier
            
        Returns:
            Place data or None
        """
        query = """
            SELECT 
                p.*,
                ci.city_name as city_name,
                ci.id as city_id,
                s.state_name as state_name,
                s.id as state_id,
                co.country_name as country_name,
                co.id as country_id
            FROM places p
            LEFT JOIN cities ci ON p.city_id = ci.id
            LEFT JOIN states s ON p.state_id = s.id
            JOIN countries co ON p.country_id = co.id
            WHERE p.id = ?
        """
        place = get_db().execute_one(query, (place_id,))
        return transform_place_row(place)
    
    @staticmethod
    def get_by_city(city_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all places in a city with full details
        
        Args:
            city_id: City identifier
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of places with all fields
        """
        query = """
            SELECT 
                p.*,
                ci.city_name,
                s.state_name,
                co.country_name
            FROM places p
            LEFT JOIN cities ci ON p.city_id = ci.id
            LEFT JOIN states s ON ci.state_id = s.id
            LEFT JOIN countries co ON s.country_id = co.id
            WHERE p.city_id = ?
            ORDER BY p.rating_tourist_priority DESC, p.place_name ASC
            LIMIT ? OFFSET ?
        """
        places = get_db().execute_query(query, (city_id, limit, offset))
        result = []
        for place in places:
            place = dict(place) if not isinstance(place, dict) else place
            # Use name_english if available, otherwise place_name
            place['name'] = place.get('name_english') or place.get('place_name', '')
            place['summary'] = place.get('ai_summary', '')
            place['rating'] = place.get('rating_tourist_priority', 0)
            place['category'] = place.get('cost', '')
            place['coordinates'] = {
                'lat': place.get('latitude'),
                'lng': place.get('longitude')
            }
            result.append(transform_place_row(place))
        return result
    
    @staticmethod
    def count_by_city(city_id: str) -> int:
        """Count places in a city"""
        query = "SELECT COUNT(*) FROM places WHERE city_id = ?"
        return get_db().execute_count(query, (city_id,))
    
    @staticmethod
    def get_by_state(state_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all places in a state
        
        Args:
            state_id: State identifier
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of places with full details
        """
        query = """
            SELECT 
                p.*,
                ci.city_name,
                s.state_name,
                co.country_name
            FROM places p
            LEFT JOIN cities ci ON p.city_id = ci.id
            LEFT JOIN states s ON ci.state_id = s.id
            LEFT JOIN countries co ON s.country_id = co.id
            WHERE ci.state_id = ?
            ORDER BY p.rating_tourist_priority DESC, p.place_name ASC
            LIMIT ? OFFSET ?
        """
        places = get_db().execute_query(query, (state_id, limit, offset))
        result = []
        for place in places:
            place = dict(place) if not isinstance(place, dict) else place
            place['name'] = place.get('name_english') or place.get('place_name', '')
            place['summary'] = place.get('ai_summary', '')
            place['rating'] = place.get('rating_tourist_priority', 0)
            place['category'] = place.get('cost', '')
            place['coordinates'] = {
                'lat': place.get('latitude'),
                'lng': place.get('longitude')
            }
            result.append(transform_place_row(place))
        return result
    
    @staticmethod
    def count_by_state(state_id: str) -> int:
        """Count places in a state"""
        query = """
            SELECT COUNT(*) 
            FROM places p 
            JOIN cities ci ON p.city_id = ci.id 
            WHERE ci.state_id = ?
        """
        return get_db().execute_count(query, (state_id,))
    
    @staticmethod
    def get_by_country(country_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all places in a country
        
        Args:
            country_id: Country identifier
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of places with full details
        """
        query = """
            SELECT 
                p.*,
                ci.city_name,
                s.state_name,
                co.country_name
            FROM places p
            LEFT JOIN cities ci ON p.city_id = ci.id
            LEFT JOIN states s ON ci.state_id = s.id
            LEFT JOIN countries co ON s.country_id = co.id
            WHERE s.country_id = ?
            ORDER BY p.rating_tourist_priority DESC, p.place_name ASC
            LIMIT ? OFFSET ?
        """
        places = get_db().execute_query(query, (country_id, limit, offset))
        result = []
        for place in places:
            place = dict(place) if not isinstance(place, dict) else place
            place['name'] = place.get('name_english') or place.get('place_name', '')
            place['summary'] = place.get('ai_summary', '')
            place['rating'] = place.get('rating_tourist_priority', 0)
            place['category'] = place.get('cost', '')
            place['coordinates'] = {
                'lat': place.get('latitude'),
                'lng': place.get('longitude')
            }
            result.append(transform_place_row(place))
        return result
    
    @staticmethod
    def count_by_country(country_id: str) -> int:
        """Count places in a country"""
        query = """
            SELECT COUNT(*) 
            FROM places p 
            JOIN cities ci ON p.city_id = ci.id 
            JOIN states s ON ci.state_id = s.id 
            WHERE s.country_id = ?
        """
        return get_db().execute_count(query, (country_id,))
    
    @staticmethod
    def search_by_name(query: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search places by name with full details
        
        Args:
            query: Search query
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of matching places with all fields
        """
        search_query = """
            SELECT 
                p.*,
                ci.city_name,
                s.state_name,
                co.country_name
            FROM places p
            LEFT JOIN cities ci ON p.city_id = ci.id
            LEFT JOIN states s ON ci.state_id = s.id
            LEFT JOIN countries co ON s.country_id = co.id
            WHERE LOWER(p.place_name) LIKE ? OR LOWER(p.name_english) LIKE ?
            ORDER BY p.rating_tourist_priority DESC
            LIMIT ? OFFSET ?
        """
        query_pattern = f'%{query.lower()}%'
        places = get_db().execute_query(search_query, (query_pattern, query_pattern, limit, offset))
        result = []
        for place in places:
            place = dict(place) if not isinstance(place, dict) else place
            place['name'] = place.get('name_english') or place.get('place_name', '')
            place['summary'] = place.get('ai_summary', '')
            place['rating'] = place.get('rating_tourist_priority', 0)
            place['category'] = place.get('cost', '')
            place['coordinates'] = {
                'lat': place.get('latitude'),
                'lng': place.get('longitude')
            }
            result.append(transform_place_row(place))
        return result
    
    @staticmethod
    def search(query: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search places by name, tags, or summary
        
        Args:
            query: Search query
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of matching places
        """
        search_query = """
            SELECT 
                p.*,
                ci.city_name as city_name,
                s.state_name as state_name,
                co.country_name as country_name,
                CASE
                    WHEN p.name LIKE ? THEN 3
                    WHEN p.tags LIKE ? THEN 2
                    WHEN p.summary LIKE ? THEN 1
                    ELSE 0
                END as relevance
            FROM places p
            LEFT JOIN cities ci ON p.city_id = ci.id
            LEFT JOIN states s ON p.state_id = s.id
            JOIN countries co ON p.country_id = co.id
            WHERE p.name LIKE ? 
                OR p.tags LIKE ?
                OR p.summary LIKE ?
            ORDER BY relevance DESC, p.rating DESC, p.name ASC
            LIMIT ? OFFSET ?
        """
        search_pattern = f"%{query}%"
        params = (
            search_pattern, search_pattern, search_pattern,
            search_pattern, search_pattern, search_pattern,
            limit, offset
        )
        places = get_db().execute_query(search_query, params)
        return [transform_place_row(place) for place in places]
    
    @staticmethod
    def count_search(query: str) -> int:
        """Count search results"""
        search_query = """
            SELECT COUNT(*) 
            FROM places 
            WHERE name LIKE ? OR tags LIKE ? OR summary LIKE ?
        """
        search_pattern = f"%{query}%"
        return get_db().execute_count(search_query, (search_pattern, search_pattern, search_pattern))


class CitiesModel:
    """Model for cities data operations"""
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """Get all cities with state and country names"""
        query = """
            SELECT c.id, c.state_id, c.city_name as name, c.latitude, c.longitude, c.created_at,
                   s.state_name, co.country_name, co.id as country_id
            FROM cities c
            LEFT JOIN states s ON c.state_id = s.id
            JOIN countries co ON s.country_id = co.id
            ORDER BY c.city_name ASC LIMIT 10000
        """
        return get_db().execute_query(query)
    
    @staticmethod
    def get_by_id(city_id: str) -> Optional[Dict[str, Any]]:
        """Get city by ID"""
        query = """
            SELECT c.id, c.state_id, c.city_name as name, c.latitude, c.longitude, c.created_at,
                   s.state_name, co.country_name, co.id as country_id
            FROM cities c
            LEFT JOIN states s ON c.state_id = s.id
            JOIN countries co ON s.country_id = co.id
            WHERE c.id = ?
        """
        return get_db().execute_one(query, (city_id,))
    
    @staticmethod
    def get_by_state(state_id: str) -> List[Dict[str, Any]]:
        """Get all cities in a state"""
        query = """
            SELECT c.id, c.state_id, c.city_name as name, c.latitude, c.longitude, c.created_at,
                   s.state_name, co.country_name, co.id as country_id
            FROM cities c
            LEFT JOIN states s ON c.state_id = s.id
            JOIN countries co ON s.country_id = co.id
            WHERE c.state_id = ?
            ORDER BY c.city_name ASC
        """
        return get_db().execute_query(query, (state_id,))
    
    @staticmethod
    def get_by_country(country_id: str) -> List[Dict[str, Any]]:
        """Get all cities in a country"""
        query = """
            SELECT c.id, c.state_id, c.city_name as name, c.latitude, c.longitude, c.created_at,
                   s.state_name, co.country_name, co.id as country_id
            FROM cities c
            LEFT JOIN states s ON c.state_id = s.id
            JOIN countries co ON s.country_id = co.id
            WHERE co.id = ?
            ORDER BY c.city_name ASC
        """
        return get_db().execute_query(query, (country_id,))


class StatesModel:
    """Model for states data operations"""
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """Get all states with country names"""
        query = """
            SELECT s.id, s.country_id, s.state_name as name, s.latitude, s.longitude, s.created_at,
                   co.country_name
            FROM states s
            JOIN countries co ON s.country_id = co.id
            ORDER BY s.state_name ASC
        """
        return get_db().execute_query(query)
    
    @staticmethod
    def get_by_id(state_id: str) -> Optional[Dict[str, Any]]:
        """Get state by ID"""
        query = """
            SELECT s.id, s.country_id, s.state_name as name, s.latitude, s.longitude, s.created_at,
                   co.country_name
            FROM states s
            JOIN countries co ON s.country_id = co.id
            WHERE s.id = ?
        """
        return get_db().execute_one(query, (state_id,))
    
    @staticmethod
    def get_by_country(country_id: str) -> List[Dict[str, Any]]:
        """Get all states in a country"""
        query = """
            SELECT s.id, s.country_id, s.state_name as name, s.latitude, s.longitude, s.created_at,
                   co.country_name
            FROM states s
            JOIN countries co ON s.country_id = co.id
            WHERE s.country_id = ?
            ORDER BY s.state_name ASC
        """
        return get_db().execute_query(query, (country_id,))


class CountriesModel:
    """Model for countries data operations"""
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """Get all countries"""
        query = "SELECT id, country_name as name, id as code FROM countries ORDER BY country_name ASC"
        return get_db().execute_query(query)
    
    @staticmethod
    def get_by_id(country_id: str) -> Optional[Dict[str, Any]]:
        """Get country by ID"""
        query = "SELECT id, country_name as name, id as code FROM countries WHERE id = ?"
        return get_db().execute_one(query, (country_id,))


class LocationSearchModel:
    """Bounded SQL lookups for the deprecated unified location search.

    This deliberately does not call the ``get_all`` helpers: a cache miss on
    the public endpoint must not load the complete countries/states/cities
    hierarchy into application memory.
    """

    @staticmethod
    def find_city(query_text: str, *, exact: bool) -> Optional[Dict[str, Any]]:
        comparator = 'LOWER(c.city_name) = LOWER(?)' if exact else 'LOWER(c.city_name) LIKE ?'
        value = query_text if exact else f'%{query_text.lower()}%'
        query = f"""
            SELECT c.id, c.city_name AS name, c.state_id,
                   s.state_name, co.id AS country_id, co.country_name
            FROM cities c
            JOIN states s ON c.state_id = s.id
            JOIN countries co ON s.country_id = co.id
            WHERE {comparator}
            ORDER BY c.city_name ASC
            LIMIT 1
        """
        return get_db().execute_one(query, (value,))

    @staticmethod
    def find_state(query_text: str, *, exact: bool) -> Optional[Dict[str, Any]]:
        comparator = 'LOWER(s.state_name) = LOWER(?)' if exact else 'LOWER(s.state_name) LIKE ?'
        value = query_text if exact else f'%{query_text.lower()}%'
        query = f"""
            SELECT s.id, s.state_name AS name, s.country_id, co.country_name
            FROM states s
            JOIN countries co ON s.country_id = co.id
            WHERE {comparator}
            ORDER BY s.state_name ASC
            LIMIT 1
        """
        return get_db().execute_one(query, (value,))

    @staticmethod
    def find_country(query_text: str, *, exact: bool) -> Optional[Dict[str, Any]]:
        comparator = 'LOWER(country_name) = LOWER(?)' if exact else 'LOWER(country_name) LIKE ?'
        value = query_text if exact else f'%{query_text.lower()}%'
        query = f"""
            SELECT id, country_name AS name
            FROM countries
            WHERE {comparator}
            ORDER BY country_name ASC
            LIMIT 1
        """
        return get_db().execute_one(query, (value,))

    @staticmethod
    def get_country_sections(
        country_id: str,
        *,
        state_limit: int = 10,
        places_per_state: int = 5,
    ) -> tuple[List[Dict[str, Any]], int]:
        """Fetch country state sections and their top places in one query."""
        query = """
            WITH selected_states AS (
                SELECT id, state_name, country_id
                FROM states
                WHERE country_id = ?
                ORDER BY state_name ASC
                LIMIT ?
            ),
            ranked_places AS (
                SELECT
                    p.*,
                    selected_states.id AS section_state_id,
                    selected_states.state_name AS section_state_name,
                    ROW_NUMBER() OVER (
                        PARTITION BY selected_states.id
                        ORDER BY p.rating_tourist_priority DESC, p.place_name ASC
                    ) AS place_rank
                FROM selected_states
                LEFT JOIN cities ci ON ci.state_id = selected_states.id
                LEFT JOIN places p ON p.city_id = ci.id
            )
            SELECT *
            FROM ranked_places
            WHERE place_rank <= ?
            ORDER BY section_state_name ASC, place_rank ASC
        """
        rows = get_db().execute_query(query, (country_id, state_limit, places_per_state))
        sections_by_id: Dict[str, Dict[str, Any]] = {}
        for raw_row in rows:
            row = dict(raw_row) if not isinstance(raw_row, dict) else raw_row
            state_id = str(row['section_state_id'])
            section = sections_by_id.setdefault(state_id, {
                'state_id': state_id,
                'state_name': row['section_state_name'],
                'state_slug': str(row['section_state_name']).lower().replace(' ', '-'),
                'place_count': 0,
                'top_places': [],
            })
            if row.get('id') is None:
                continue
            row['name'] = row.get('name_english') or row.get('place_name', '')
            row['summary'] = row.get('ai_summary', '')
            row['rating'] = row.get('rating_tourist_priority', 0)
            row['category'] = row.get('cost', '')
            row['coordinates'] = {
                'lat': row.get('latitude'),
                'lng': row.get('longitude'),
            }
            section['top_places'].append(transform_place_row(row))
            section['place_count'] += 1

        # Match the former response contract: omit states without a place.
        sections = [s for s in sections_by_id.values() if s['top_places']]
        state_count = get_db().execute_count(
            'SELECT COUNT(*) FROM states WHERE country_id = ?', (country_id,),
        )
        return sections, state_count

    @staticmethod
    def search_cities(
        query_text: str,
        *,
        country_id: str = '',
        state_id: str = '',
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search cities in SQL instead of filtering a full city table."""
        conditions = ['LOWER(c.city_name) LIKE ?']
        params: list[Any] = [f'%{query_text.lower()}%']
        if country_id:
            conditions.append('co.id = ?')
            params.append(country_id)
        if state_id:
            conditions.append('s.id = ?')
            params.append(state_id)
        params.append(limit)
        query = f"""
            SELECT c.id, c.state_id, c.city_name AS name, c.latitude, c.longitude,
                   co.id AS country_id, s.state_name, co.country_name
            FROM cities c
            JOIN states s ON c.state_id = s.id
            JOIN countries co ON s.country_id = co.id
            WHERE {' AND '.join(conditions)}
            ORDER BY c.city_name ASC
            LIMIT ?
        """
        return get_db().execute_query(query, tuple(params))

    @staticmethod
    def autocomplete(query_text: str, limit: int) -> List[Dict[str, Any]]:
        """Return a bounded cross-hierarchy destination search result set."""
        like = f'%{query_text.lower()}%'
        starts_with = f'{query_text.lower()}%'
        # Fetch a small dedupe cushion, then let the route apply its stable
        # public sort and display-name de-duplication.
        row_limit = min(max(limit * 4, 20), 200)
        query = """
            SELECT * FROM (
                SELECT id, 'country' AS location_type, country_name AS name,
                       NULL AS latitude, NULL AS longitude, id AS country_id,
                       country_name, NULL AS state_id, NULL AS state_name,
                       NULL AS city_id, NULL AS city_name
                FROM countries
                WHERE LOWER(country_name) LIKE ?
                UNION ALL
                SELECT s.id, 'state' AS location_type, s.state_name AS name,
                       s.latitude, s.longitude, s.country_id, co.country_name,
                       s.id AS state_id, s.state_name, NULL AS city_id, NULL AS city_name
                FROM states s JOIN countries co ON s.country_id = co.id
                WHERE LOWER(s.state_name) LIKE ?
                UNION ALL
                SELECT c.id, 'city' AS location_type, c.city_name AS name,
                       c.latitude, c.longitude, co.id AS country_id, co.country_name,
                       s.id AS state_id, s.state_name, c.id AS city_id, c.city_name
                FROM cities c
                JOIN states s ON c.state_id = s.id
                JOIN countries co ON s.country_id = co.id
                WHERE LOWER(c.city_name) LIKE ?
                UNION ALL
                SELECT p.id, 'place' AS location_type,
                       COALESCE(p.name_english, p.place_name) AS name,
                       p.latitude, p.longitude, s.country_id, co.country_name,
                       s.id AS state_id, s.state_name, c.id AS city_id, c.city_name
                FROM places p
                LEFT JOIN cities c ON p.city_id = c.id
                LEFT JOIN states s ON c.state_id = s.id
                LEFT JOIN countries co ON s.country_id = co.id
                WHERE LOWER(p.place_name) LIKE ? OR LOWER(p.name_english) LIKE ?
            )
            ORDER BY
                CASE
                    WHEN LOWER(name) = LOWER(?) THEN 0
                    WHEN LOWER(name) LIKE ? THEN 1
                    ELSE 2
                END,
                CASE location_type
                    WHEN 'city' THEN 0 WHEN 'state' THEN 1
                    WHEN 'country' THEN 2 ELSE 3
                END,
                name ASC
            LIMIT ?
        """
        return get_db().execute_query(
            query,
            (like, like, like, like, like, query_text, starts_with, row_limit),
        )
