"""
Data models for places API
Provides query methods for places, cities, states, and countries.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from app.api.utils.database import get_db

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
