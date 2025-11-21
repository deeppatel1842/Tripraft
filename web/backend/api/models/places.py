"""
Data models for places API
Provides query methods for places, cities, states, and countries.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from ..utils.database import get_db

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
                ci.name as city_name,
                ci.id as city_id,
                s.name as state_name,
                s.id as state_id,
                co.name as country_name,
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
        Get all places in a city
        
        Args:
            city_id: City identifier
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of places
        """
        query = """
            SELECT 
                p.*,
                ci.name as city_name,
                s.name as state_name,
                co.name as country_name
            FROM places p
            LEFT JOIN cities ci ON p.city_id = ci.id
            LEFT JOIN states s ON p.state_id = s.id
            JOIN countries co ON p.country_id = co.id
            WHERE p.city_id = ?
            ORDER BY p.rating DESC, p.name ASC
            LIMIT ? OFFSET ?
        """
        places = get_db().execute_query(query, (city_id, limit, offset))
        return [transform_place_row(place) for place in places]
    
    @staticmethod
    def count_by_city(city_id: str) -> int:
        """Count places in a city"""
        query = "SELECT COUNT(*) FROM places WHERE city_id = ?"
        return get_db().execute_count(query, (city_id,))
    
    @staticmethod
    def get_by_state(state_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all places in a state (without city)
        
        Args:
            state_id: State identifier
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of places
        """
        query = """
            SELECT 
                p.*,
                s.name as state_name,
                co.name as country_name
            FROM places p
            LEFT JOIN states s ON p.state_id = s.id
            JOIN countries co ON p.country_id = co.id
            WHERE p.state_id = ? AND p.city_id IS NULL
            ORDER BY p.rating DESC, p.name ASC
            LIMIT ? OFFSET ?
        """
        places = get_db().execute_query(query, (state_id, limit, offset))
        return [transform_place_row(place) for place in places]
    
    @staticmethod
    def count_by_state(state_id: str) -> int:
        """Count places in a state (without city)"""
        query = "SELECT COUNT(*) FROM places WHERE state_id = ? AND city_id IS NULL"
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
            List of places
        """
        query = """
            SELECT 
                p.*,
                ci.name as city_name,
                s.name as state_name,
                co.name as country_name
            FROM places p
            LEFT JOIN cities ci ON p.city_id = ci.id
            LEFT JOIN states s ON p.state_id = s.id
            JOIN countries co ON p.country_id = co.id
            WHERE p.country_id = ?
            ORDER BY p.rating DESC, p.name ASC
            LIMIT ? OFFSET ?
        """
        places = get_db().execute_query(query, (country_id, limit, offset))
        return [transform_place_row(place) for place in places]
    
    @staticmethod
    def count_by_country(country_id: str) -> int:
        """Count places in a country"""
        query = "SELECT COUNT(*) FROM places WHERE country_id = ?"
        return get_db().execute_count(query, (country_id,))
    
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
                ci.name as city_name,
                s.name as state_name,
                co.name as country_name,
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
    def get_by_id(city_id: str) -> Optional[Dict[str, Any]]:
        """Get city by ID"""
        query = """
            SELECT c.*, s.name as state_name, co.name as country_name
            FROM cities c
            JOIN states s ON c.state_id = s.id
            JOIN countries co ON c.country_id = co.id
            WHERE c.id = ?
        """
        return get_db().execute_one(query, (city_id,))
    
    @staticmethod
    def get_by_state(state_id: str) -> List[Dict[str, Any]]:
        """Get all cities in a state"""
        query = """
            SELECT c.*, s.name as state_name, co.name as country_name
            FROM cities c
            JOIN states s ON c.state_id = s.id
            JOIN countries co ON c.country_id = co.id
            WHERE c.state_id = ?
            ORDER BY c.name ASC
        """
        return get_db().execute_query(query, (state_id,))
    
    @staticmethod
    def get_by_country(country_id: str) -> List[Dict[str, Any]]:
        """Get all cities in a country"""
        query = """
            SELECT c.*, s.name as state_name, co.name as country_name
            FROM cities c
            JOIN states s ON c.state_id = s.id
            JOIN countries co ON c.country_id = co.id
            WHERE c.country_id = ?
            ORDER BY c.name ASC
        """
        return get_db().execute_query(query, (country_id,))


class StatesModel:
    """Model for states data operations"""
    
    @staticmethod
    def get_by_id(state_id: str) -> Optional[Dict[str, Any]]:
        """Get state by ID"""
        query = """
            SELECT s.*, co.name as country_name
            FROM states s
            JOIN countries co ON s.country_id = co.id
            WHERE s.id = ?
        """
        return get_db().execute_one(query, (state_id,))
    
    @staticmethod
    def get_by_country(country_id: str) -> List[Dict[str, Any]]:
        """Get all states in a country"""
        query = """
            SELECT s.*, co.name as country_name
            FROM states s
            JOIN countries co ON s.country_id = co.id
            WHERE s.country_id = ?
            ORDER BY s.name ASC
        """
        return get_db().execute_query(query, (country_id,))


class CountriesModel:
    """Model for countries data operations"""
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """Get all countries"""
        query = "SELECT * FROM countries ORDER BY name ASC"
        return get_db().execute_query(query)
    
    @staticmethod
    def get_by_id(country_id: str) -> Optional[Dict[str, Any]]:
        """Get country by ID"""
        query = "SELECT * FROM countries WHERE id = ?"
        return get_db().execute_one(query, (country_id,))
