"""
Destination Service (formerly PlacesService)
Fetches destination/places data from the travel database.

Author: Group Planner System
Version: 2.1
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.config import Config
from app.infrastructure.db.travel_db import travel_db

logger = logging.getLogger(__name__)


class DestinationService:
    """Destination lookup service using travel_data_complete.db via TravelDatabase."""
    
    def __init__(self):
        """Initialize service."""
        logger.info("DestinationService initialized")

    @staticmethod
    def _resolve_location(cursor, city_name: str) -> tuple:
        """
        Resolve a location string to (city_ids, coordinates).

        Tries city -> state -> country in order.
        Returns (list[int], dict|None).
        """
        location_parts = [part.strip() for part in city_name.split(',')]
        search_name = location_parts[0]

        logger.info("Resolving location: '%s' -> parsed to '%s'", city_name, search_name)

        # Try city
        cursor.execute("""
            SELECT id, city_name, latitude, longitude
            FROM cities
            WHERE city_name = ? COLLATE NOCASE
            LIMIT 1
        """, (search_name,))
        city_row = cursor.fetchone()
        if city_row:
            coords = {'latitude': city_row['latitude'], 'longitude': city_row['longitude']}
            logger.info("Found city: %s", search_name)
            return [city_row['id']], coords

        # Try state
        cursor.execute("""
            SELECT id, state_name, latitude, longitude
            FROM states
            WHERE state_name = ? COLLATE NOCASE
            LIMIT 1
        """, (search_name,))
        state_row = cursor.fetchone()
        if state_row:
            coords = {'latitude': state_row['latitude'], 'longitude': state_row['longitude']}
            cursor.execute("SELECT id FROM cities WHERE state_id = ?", (state_row['id'],))
            city_ids = [row['id'] for row in cursor.fetchall()]
            logger.info("Found state: %s, with %d cities", search_name, len(city_ids))
            return city_ids, coords

        # Try country
        cursor.execute("""
            SELECT id, country_name
            FROM countries
            WHERE country_name = ? COLLATE NOCASE
            LIMIT 1
        """, (search_name,))
        country_row = cursor.fetchone()
        if country_row:
            cursor.execute("""
                SELECT c.id, c.latitude, c.longitude FROM cities c
                JOIN states s ON c.state_id = s.id
                WHERE s.country_id = ?
                LIMIT 1
            """, (country_row['id'],))
            first_city = cursor.fetchone()
            coords = None
            if first_city:
                coords = {'latitude': first_city['latitude'], 'longitude': first_city['longitude']}
            cursor.execute("""
                SELECT c.id FROM cities c
                JOIN states s ON c.state_id = s.id
                WHERE s.country_id = ?
            """, (country_row['id'],))
            city_ids = [row['id'] for row in cursor.fetchall()]
            logger.info("Found country: %s, with %d cities", search_name, len(city_ids))
            return city_ids, coords

        logger.warning("Location not found: %s (original: %s)", search_name, city_name)
        return [], None
    
    def search_places_by_city(self, city_name: str, limit: int = Config.SEARCH_DEFAULT_LIMIT) -> tuple:
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
            with travel_db.get_connection() as conn:
                cursor = conn.cursor()

                city_ids, city_coords = self._resolve_location(cursor, city_name)

                if not city_ids:
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
                        p.official_website,
                        p.rating_tourist_priority,
                        p.rating_traveler_experience,
                        p.ai_summary,
                        p.suggested_duration,
                        p.rank_score,
                        ph.thumbnail_url as image_url,
                        oh.monday, oh.tuesday, oh.wednesday, oh.thursday,
                        oh.friday, oh.saturday, oh.sunday, oh.notes as hours_notes
                    FROM places p
                    LEFT JOIN photos ph ON ph.place_id = p.id
                    LEFT JOIN opening_hours oh ON oh.place_id = p.id
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
                    # Build opening_hours dict only if data exists
                    opening_hours = None
                    if row['monday']:
                        opening_hours = {
                            'monday': row['monday'],
                            'tuesday': row['tuesday'],
                            'wednesday': row['wednesday'],
                            'thursday': row['thursday'],
                            'friday': row['friday'],
                            'saturday': row['saturday'],
                            'sunday': row['sunday'],
                            'notes': row['hours_notes'] or '',
                        }

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
                        'official_website': row['official_website'] if row['official_website'] and row['official_website'].startswith('http') else None,
                        'category': 'attraction',
                        'rating': row['rating_tourist_priority'],
                        'traveler_rating': row['rating_traveler_experience'],
                        'description': row['ai_summary'],
                        'suggested_duration': row['suggested_duration'],
                        'rank_score': row['rank_score'],
                        'image_url': row['image_url'],
                        'opening_hours': opening_hours,
                    }
                    places.append(place)

                logger.info("Found %d places for %s (from %d cities)", len(places), city_name, len(city_ids))
                return places, city_coords

        except Exception as e:
            logger.error("Error searching places for %s: %s", city_name, e)
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
            with travel_db.get_connection() as conn:
                cursor = conn.cursor()

                city_ids, _ = self._resolve_location(cursor, city_name)

                if not city_ids:
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

                logger.info("Found %d restaurants for %s", len(restaurants), city_name)
                return restaurants

        except Exception as e:
            logger.error("Error getting restaurants for %s: %s", city_name, e)
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
        
        logger.info("Retrieved %d places + %d restaurants = %d total items", len(places_data), len(restaurants_data), len(all_items))
        
        return all_items, city_coords

    def get_destination_places(self, destination: str, category: str = 'all', limit: int = Config.GP_DEFAULT_LIMIT) -> Dict[str, Any]:
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
            logger.error("Error in get_destination_places: %s", e)
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
            logger.error("Error in get_top_places: %s", e)
            return {'places': [], 'count': 0}


# Backward-compatible alias
PlacesService = DestinationService



