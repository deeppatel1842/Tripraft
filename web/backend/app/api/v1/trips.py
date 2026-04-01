"""
Trip Planner API Routes

REST API endpoints for generating trip itineraries.
Uses SQL-based places service for intelligent trip planning.

Endpoints:
- POST /api/trip-planner/generate - Generate trip itinerary
- GET /api/trip-planner/cities - List available cities
- GET /api/trip-planner/cities/search?q={query} - Search cities
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.api.utils.responses import (created_response, error_response,
                                     success_response)
from app.api.utils.validators import validate_schema
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.infrastructure.cache.redis import cache_response
from app.infrastructure.db.travel_db import travel_db
from app.schemas.trips import TripGenerateSchema
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

# Blueprint
trip_planner_bp = Blueprint('trip_planner', __name__, url_prefix='/api/v1/trip-planner')


def _format_time(start: float) -> int:
    """Format response time in ms."""
    return int((time.time() - start) * 1000)


@trip_planner_bp.route('/generate', methods=['POST', 'OPTIONS'])
@limit_api(Config.RATE_LIMITS['create'])
@validate_schema(TripGenerateSchema)
def generate_trip():
    """
    Generate a trip itinerary for a city.
    
    Request Body:
        {
            "city": "San Diego",        # Required: City name
            "days": 3,                   # Optional: Number of days (1-14, default 3)
            "pacing": "M",               # Optional: R=Relaxed, M=Moderate, P=Packed
            "exclude": "museums,parks",  # Optional: Comma-separated tags to exclude
            "require": "beach,viewpoint" # Optional: Comma-separated tags to require
            "places": "zoo,balboa"       # Optional: Specific place names to include
        }
    
    Returns:
        JSON response with complete itinerary
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return success_response()
    
    start = time.time()
    
    try:
        data = g.validated_data
        
        city = (data.get('city') or data.get('destination') or '').strip()
        if not city:
            return error_response("City name is required")
        
        days = data.get('days', 3)
        
        pacing = data.get('pacing', 'M').upper()
        
        # Pacing configuration
        pacing_config = Config.TRIP_PACING
        
        if pacing not in pacing_config:
            valid = ', '.join(sorted(pacing_config.keys()))
            return error_response(f"Invalid pacing '{pacing}'. Valid: {valid}", 400)
        
        config = pacing_config[pacing]
        stops_per_day = config['stops_per_day']
        
        # Get places for the city
        with travel_db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find city
            cursor.execute("""
                SELECT c.id, c.city_name, c.latitude, c.longitude,
                       s.state_name, co.country_name
                FROM cities c
                JOIN states s ON c.state_id = s.id
                JOIN countries co ON s.country_id = co.id
                WHERE c.city_name LIKE ? COLLATE NOCASE
                LIMIT 1
            """, (f'%{city}%',))
            
            city_row = cursor.fetchone()
            if not city_row:
                return error_response(f"City '{city}' not found", 404)
            
            city_id = city_row['id']
            city_info = {
                'name': city_row['city_name'],
                'state': city_row['state_name'],
                'country': city_row['country_name'],
                'coordinates': {
                    'latitude': city_row['latitude'],
                    'longitude': city_row['longitude']
                }
            }
            
            # Get places with photos
            total_places_needed = days * stops_per_day + Config.TRIP_EXTRA_PLACES_BUFFER
            
            cursor.execute("""
                SELECT 
                    p.id,
                    p.place_name,
                    p.name_english,
                    p.latitude,
                    p.longitude,
                    p.address,
                    p.rating_tourist_priority,
                    p.rating_traveler_experience,
                    p.ai_summary,
                    p.suggested_duration,
                    p.rank_score,
                    p.sunrise_view,
                    p.sunset_view,
                    p.cost,
                    ph.thumbnail_url as photo_url
                FROM places p
                LEFT JOIN photos ph ON ph.place_id = p.id
                WHERE p.city_id = ?
                    AND p.latitude IS NOT NULL 
                    AND p.longitude IS NOT NULL
                GROUP BY p.id
                ORDER BY p.rank_score DESC
                LIMIT ?
            """, (city_id, total_places_needed))
            
            places = []
            for row in cursor.fetchall():
                place = {
                    'id': row['id'],
                    'name': row['name_english'] or row['place_name'],
                    'place_name': row['place_name'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'coordinates': {
                        'latitude': row['latitude'],
                        'longitude': row['longitude']
                    },
                    'address': row['address'] or '',
                    'rating': row['rating_tourist_priority'] or 4.0,
                    'description': row['ai_summary'] or '',
                    'suggested_duration': row['suggested_duration'] or '1-2 hours',
                    'rank_score': row['rank_score'] or 0.5,
                    'sunrise_view': row['sunrise_view'] or 0,
                    'sunset_view': row['sunset_view'] or 0,
                    'cost': row['cost'] or 'medium',
                    'photo': row['photo_url']
                }
                places.append(place)
            
            # Get tags for places
            place_ids = [p['id'] for p in places]
            if place_ids:
                placeholders = ','.join('?' * len(place_ids))
                cursor.execute(f"""
                    SELECT pt.place_id, t.tag_name
                    FROM place_tags pt
                    JOIN tags t ON pt.tag_id = t.id
                    WHERE pt.place_id IN ({placeholders})
                """, place_ids)
                
                tags_by_place = {}
                for row in cursor.fetchall():
                    pid = row['place_id']
                    if pid not in tags_by_place:
                        tags_by_place[pid] = []
                    tags_by_place[pid].append(row['tag_name'])
                
                for place in places:
                    place['tags'] = tags_by_place.get(place['id'], [])
        
        if not places:
            return error_response(f"No places found for city '{city}'", 404)
        
        # Generate itinerary
        itinerary = []
        place_index = 0
        
        for day_num in range(1, days + 1):
            day_stops = []
            
            for stop_num in range(stops_per_day):
                if place_index >= len(places):
                    break
                
                place = places[place_index]
                place_index += 1
                
                # Calculate arrival time
                hour = Config.TRIP_START_HOUR + (stop_num * Config.TRIP_HOURS_BETWEEN_STOPS)
                arrival_time = f"{hour:02d}:00"
                
                stop = {
                    'arrivalTime': arrival_time,
                    'name': place['name'],
                    'icon': 'mapPin',
                    'color': 'text-purple-600',
                    'hours': f"{hour:02d}:00-{(hour+Config.TRIP_HOURS_BETWEEN_STOPS):02d}:00",
                    'visitDuration': place['suggested_duration'],
                    'suggestedDuration': place['suggested_duration'],
                    'travelToNext': '15 min',
                    'lunch': stop_num == Config.TRIP_LUNCH_AFTER_STOP,
                    'endOfDay': stop_num == stops_per_day - 1,
                    'place_data': place
                }
                day_stops.append(stop)
            
            itinerary.append({
                'day': day_num,
                'title': f"Day {day_num}",
                'stops': day_stops
            })
        
        # Get high ranked places not in itinerary
        used_ids = set(p['id'] for day in itinerary for stop in day['stops'] for p in [stop['place_data']])
        high_ranked = [p for p in places if p['id'] not in used_ids][:5]
        
        # Get sunrise/sunset places
        sunrise_places = [p for p in places if p.get('sunrise_view', 0) == 1][:3]
        sunset_places = [p for p in places if p.get('sunset_view', 0) == 1][:3]
        
        result = {
            'title': f"{days}-Day {city_info['name']} Trip",
            'city': city_info,
            'airport': None,
            'pacing': config['name'],
            'itinerary': itinerary,
            'highRankedPlaces': high_ranked,
            'specialPlaces': {
                'early_morning': sunrise_places,
                'late_night': sunset_places
            }
        }
        
        return created_response(data=result, message='Trip generated')
        
    except Exception as e:
        logger.error(f"Error generating trip: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)


@trip_planner_bp.route('/cities', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@cache_response(key_prefix='trips:cities', ttl=Config.CACHE_TTLS['categories'])
def list_cities():
    """
    List all available cities for trip planning.
    
    Query Parameters:
        limit (optional): Max cities to return (default 50)
        country (optional): Filter by country name
    
    Returns:
        JSON list of cities with basic info
    """
    start = time.time()
    
    try:
        limit = int(request.args.get('limit', Config.GP_DEFAULT_LIMIT))
        limit = max(1, min(100, limit))
        
        country_filter = request.args.get('country', '').strip()
        
        with travel_db.get_connection() as conn:
            cursor = conn.cursor()
            
            if country_filter:
                cursor.execute("""
                    SELECT c.id, c.city_name, s.state_name, co.country_name,
                           c.latitude, c.longitude
                    FROM cities c
                    JOIN states s ON c.state_id = s.id
                    JOIN countries co ON s.country_id = co.id
                    WHERE co.country_name LIKE ? COLLATE NOCASE
                    ORDER BY c.city_name
                    LIMIT ?
                """, (f'%{country_filter}%', limit))
            else:
                cursor.execute("""
                    SELECT c.id, c.city_name, s.state_name, co.country_name,
                           c.latitude, c.longitude
                    FROM cities c
                    JOIN states s ON c.state_id = s.id
                    JOIN countries co ON s.country_id = co.id
                    ORDER BY c.city_name
                    LIMIT ?
                """, (limit,))
            
            cities = []
            for row in cursor.fetchall():
                cities.append({
                    'id': row['id'],
                    'name': row['city_name'],
                    'state': row['state_name'],
                    'country': row['country_name'],
                    'coordinates': {
                        'latitude': row['latitude'],
                        'longitude': row['longitude']
                    }
                })
        
        return success_response(
            data=cities,
            meta={'count': len(cities)}
        )
        
    except Exception as e:
        logger.error(f"Error listing cities: {e}")
        return error_response(str(e), 500)


@trip_planner_bp.route('/cities/search', methods=['GET'])
@limit_api(Config.RATE_LIMITS['search'])
@cache_response(key_prefix='trips:city_search', ttl=Config.CACHE_TTLS['city_search'])
def search_cities():
    """
    Search for cities by name.
    
    Query Parameters:
        q (required): Search query
        limit (optional): Max results (default 10)
    
    Returns:
        JSON list of matching cities
    """
    start = time.time()
    
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return error_response("Query parameter 'q' is required")
        
        limit = int(request.args.get('limit', 10))
        limit = max(1, min(50, limit))
        
        with travel_db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.id, c.city_name, s.state_name, co.country_name,
                       c.latitude, c.longitude
                FROM cities c
                JOIN states s ON c.state_id = s.id
                JOIN countries co ON s.country_id = co.id
                WHERE c.city_name LIKE ? COLLATE NOCASE
                ORDER BY 
                    CASE 
                        WHEN c.city_name LIKE ? THEN 1
                        ELSE 2
                    END,
                    c.city_name
                LIMIT ?
            """, (f'%{query}%', f'{query}%', limit))
            
            cities = []
            for row in cursor.fetchall():
                cities.append({
                    'id': row['id'],
                    'name': row['city_name'],
                    'state': row['state_name'],
                    'country': row['country_name'],
                    'display_name': f"{row['city_name']}, {row['country_name']}",
                    'coordinates': {
                        'latitude': row['latitude'],
                        'longitude': row['longitude']
                    }
                })
        
        return success_response(
            data=cities,
            meta={'count': len(cities), 'query': query}
        )
        
    except Exception as e:
        logger.error(f"Error searching cities: {e}")
        return error_response(str(e), 500)
