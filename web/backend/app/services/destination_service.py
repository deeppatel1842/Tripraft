"""
Destination Service (formerly PlacesService)
Fetches destination/places data directly from SQLite database

Author: Group Planner System
Version: 2.0
"""

import logging
import sqlite3
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DestinationService:
    """Destination lookup service using local travel_data_complete.db"""
    
    def __init__(self, db_path: str = None):
        """Initialize with database path."""
        if db_path is None:
            import os

            # Default path to travel database
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(backend_dir, 'database', 'travel_data_complete.db')
        
        self.db_path = db_path
        logger.info(f"DestinationService initialized with database: {db_path}")
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def search_places_by_city(self, city_name: str, limit: int = 20) -> tuple:
        """
        Search for places in a specific city, state, or country.
        
        If country is selected: Get places from all cities in that country
        If state is selected: Get places from all cities in that state
        If city is selected: Get places from that specific city
        
        Args:
            city_name: City, state, or country name to search for 
                      (can be "City, State, Country" format)
            limit: Maximum number of results
            
        Returns:
            Tuple of (places_list, coordinates_dict)
        """
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            city_coords = None
            city_ids = []
            
            # Parse the location string - it may be "City, State, Country" format
            location_parts = [part.strip() for part in city_name.split(',')]
            search_name = location_parts[0]  # Use first part (city name)
            
            logger.info(f"Searching for location: '{city_name}' -> parsed to '{search_name}'")
            
            # First, try to find as a city
            cursor.execute("""
                SELECT id, city_name, latitude, longitude
                FROM cities
                WHERE city_name = ? COLLATE NOCASE
                LIMIT 1
            """, (search_name,))
            
            city_row = cursor.fetchone()
            
            if city_row:
                # Found as a city - use this city only
                city_ids = [city_row['id']]
                city_coords = {
                    'latitude': city_row['latitude'],
                    'longitude': city_row['longitude']
                }
                logger.info(f"Found city: {search_name}")
            else:
                # Not a city, try as state
                cursor.execute("""
                    SELECT s.id, s.state_name, s.latitude, s.longitude
                    FROM states s
                    WHERE s.state_name = ? COLLATE NOCASE
                    LIMIT 1
                """, (search_name,))
                
                state_row = cursor.fetchone()
                if state_row:
                    # Found as state - get all cities in this state
                    city_coords = {
                        'latitude': state_row['latitude'],
                        'longitude': state_row['longitude']
                    }
                    cursor.execute("""
                        SELECT id FROM cities
                        WHERE state_id = ?
                    """, (state_row['id'],))
                    city_ids = [row['id'] for row in cursor.fetchall()]
                    logger.info(f"Found state: {search_name}, with {len(city_ids)} cities")
                else:
                    # Not a state either, try as country
                    cursor.execute("""
                        SELECT c.id, c.country_name
                        FROM countries c
                        WHERE c.country_name = ? COLLATE NOCASE
                        LIMIT 1
                    """, (search_name,))
                    
                    country_row = cursor.fetchone()
                    if country_row:
                        # Found as country - get first city coordinates
                        cursor.execute("""
                            SELECT c.id, c.latitude, c.longitude FROM cities c
                            JOIN states s ON c.state_id = s.id
                            WHERE s.country_id = ?
                            LIMIT 1
                        """, (country_row['id'],))
                        first_city = cursor.fetchone()
                        if first_city:
                            city_coords = {
                                'latitude': first_city['latitude'],
                                'longitude': first_city['longitude']
                            }
                        # Get all cities in this country
                        cursor.execute("""
                            SELECT c.id FROM cities c
                            JOIN states s ON c.state_id = s.id
                            WHERE s.country_id = ?
                        """, (country_row['id'],))
                        city_ids = [row['id'] for row in cursor.fetchall()]
                        logger.info(f"Found country: {search_name}, with {len(city_ids)} cities")
                    else:
                        logger.warning(f"Location not found: {search_name} (original: {city_name})")
                        return [], None
            
            # If no cities found, return empty
            if not city_ids:
                logger.warning(f"No cities found for location: {city_name}")
                return [], city_coords
            
            # Now get places for these cities with photos
            placeholders = ','.join('?' * len(city_ids))
            query = f"""
                SELECT 
                    p.id,
                    p.place_name,
                    p.name_english,
                    p.city_id,
                    p.latitude,
                    p.longitude,
                    p.address,
                    p.rating_tourist_priority,
                    p.rating_traveler_experience,
                    p.ai_summary,
                    p.suggested_duration,
                    p.rank_score,
                    ph.thumbnail_url as image_url
                FROM places p
                LEFT JOIN photos ph ON ph.place_id = p.id
                WHERE p.city_id IN ({placeholders})
                    AND p.latitude IS NOT NULL 
                    AND p.longitude IS NOT NULL
                GROUP BY p.id
                ORDER BY p.rating_tourist_priority DESC, p.rating_traveler_experience DESC
                LIMIT ?
            """
            cursor.execute(query, city_ids + [limit])
            
            places = []
            for row in cursor.fetchall():
                place = {
                    'id': row['id'],
                    'name': row['name_english'] or row['place_name'],
                    'place_name': row['place_name'],
                    'city_id': row['city_id'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'coordinates': {
                        'latitude': row['latitude'],
                        'longitude': row['longitude']
                    },
                    'address': row['address'],
                    'category': 'attraction',
                    'rating': row['rating_tourist_priority'],
                    'traveler_rating': row['rating_traveler_experience'],
                    'description': row['ai_summary'],
                    'suggested_duration': row['suggested_duration'],
                    'rank_score': row['rank_score'],
                    'image_url': row['image_url']
                }
                places.append(place)
            
            conn.close()
            logger.info(f"Found {len(places)} places for {city_name} (from {len(city_ids)} cities)")
            
            # Return tuple of (places, coordinates)
            return places, city_coords
            
        except Exception as e:
            logger.error(f"Error searching places for {city_name}: {e}")
            import traceback
            traceback.print_exc()
            return [], None
    
    def get_restaurants_by_city(self, city_name: str, limit: int = 4) -> List[Dict[str, Any]]:
        """
        Get restaurants for a specific city, state, or country.
        
        Args:
            city_name: City, state, or country name (can be "City, State, Country" format)
            limit: Maximum number of results
            
        Returns:
            List of restaurant dictionaries
        """
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            city_ids = []
            
            # Parse the location string - it may be "City, State, Country" format
            location_parts = [part.strip() for part in city_name.split(',')]
            search_name = location_parts[0]  # Use first part (city name)
            
            logger.info(f"Searching restaurants for: '{city_name}' -> parsed to '{search_name}'")
            
            # First, try to find as a city
            cursor.execute("""
                SELECT id FROM cities
                WHERE city_name = ? COLLATE NOCASE
                LIMIT 1
            """, (search_name,))
            
            city_row = cursor.fetchone()
            if city_row:
                city_ids = [city_row['id']]
            else:
                # Try as state
                cursor.execute("""
                    SELECT id FROM states
                    WHERE state_name = ? COLLATE NOCASE
                    LIMIT 1
                """, (search_name,))
                
                state_row = cursor.fetchone()
                if state_row:
                    cursor.execute("SELECT id FROM cities WHERE state_id = ?", (state_row['id'],))
                    city_ids = [row['id'] for row in cursor.fetchall()]
                else:
                    # Try as country
                    cursor.execute("""
                        SELECT id FROM countries
                        WHERE country_name = ? COLLATE NOCASE
                        LIMIT 1
                    """, (search_name,))
                    
                    country_row = cursor.fetchone()
                    if country_row:
                        cursor.execute("""
                            SELECT c.id FROM cities c
                            JOIN states s ON c.state_id = s.id
                            WHERE s.country_id = ?
                        """, (country_row['id'],))
                        city_ids = [row['id'] for row in cursor.fetchall()]
            
            if not city_ids:
                logger.warning(f"Location not found for restaurants: {search_name}")
                return []
            
            # Get restaurants from restaurants table
            placeholders = ','.join('?' * len(city_ids))
            query = f"""
                SELECT 
                    id,
                    restaurant_name,
                    latitude,
                    longitude
                FROM restaurants
                WHERE city_id IN ({placeholders})
                    AND latitude IS NOT NULL 
                    AND longitude IS NOT NULL
                LIMIT ?
            """
            cursor.execute(query, city_ids + [limit])
            
            restaurants = []
            for row in cursor.fetchall():
                restaurant = {
                    'id': row['id'],
                    'name': row['restaurant_name'],
                    'place_name': row['restaurant_name'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'coordinates': {
                        'latitude': row['latitude'],
                        'longitude': row['longitude']
                    },
                    'address': '',
                    'category': 'restaurant',
                    'rating': None,
                    'description': None,
                    'suggested_duration': '1-2 hours'
                }
                restaurants.append(restaurant)
            
            conn.close()
            logger.info(f"Found {len(restaurants)} restaurants for {city_name}")
            return restaurants
            
        except Exception as e:
            logger.error(f"Error getting restaurants for {city_name}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_all_places_and_restaurants(self, city_name: str, places_limit: int = 27, restaurants_limit: int = 4) -> tuple:
        """
        Get all places and restaurants for a city.
        
        Args:
            city_name: City name
            places_limit: Max places to return
            restaurants_limit: Max restaurants to return
            
        Returns:
            Tuple of (all_items_list, city_coordinates)
        """
        places_data, city_coords = self.search_places_by_city(city_name, places_limit)
        restaurants_data = self.get_restaurants_by_city(city_name, restaurants_limit)
        
        # Combine all items
        all_items = places_data + restaurants_data
        
        logger.info(f"Retrieved {len(places_data)} places + {len(restaurants_data)} restaurants = {len(all_items)} total items")
        
        return all_items, city_coords

    def get_destination_places(self, destination: str, category: str = 'all', limit: int = 50) -> Dict[str, Any]:
        """
        Get places for a destination.
        
        Args:
            destination: City, state, or country name
            category: Filter by category ('all', 'attraction', 'restaurant')
            limit: Maximum number of results
            
        Returns:
            Dictionary with places, count, attractions, restaurants
        """
        try:
            all_items, coords = self.get_all_places_and_restaurants(
                destination, 
                places_limit=limit,
                restaurants_limit=min(limit // 5, 20)  # ~20% restaurants
            )
            
            # Filter by category if needed
            if category == 'restaurant':
                items = [p for p in all_items if p.get('category') == 'restaurant']
            elif category == 'attraction':
                items = [p for p in all_items if p.get('category') != 'restaurant']
            else:
                items = all_items
            
            attractions = len([p for p in items if p.get('category') != 'restaurant'])
            restaurants = len([p for p in items if p.get('category') == 'restaurant'])
            
            return {
                'places': items,
                'count': len(items),
                'attractions': attractions,
                'restaurants': restaurants,
                'coordinates': coords
            }
        except Exception as e:
            logger.error(f"Error in get_destination_places: {e}")
            return {'places': [], 'count': 0, 'attractions': 0, 'restaurants': 0}

    def get_top_places(self, destination: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get top-rated places for a destination.
        
        Args:
            destination: City, state, or country name
            limit: Maximum number of results
            
        Returns:
            Dictionary with top places
        """
        try:
            places, coords = self.search_places_by_city(destination, limit)
            
            # Already sorted by rating in SQL query
            return {
                'places': places,
                'count': len(places),
                'coordinates': coords
            }
        except Exception as e:
            logger.error(f"Error in get_top_places: {e}")
            return {'places': [], 'count': 0}


# Backward-compatible alias
PlacesService = DestinationService

