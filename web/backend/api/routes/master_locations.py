"""
Master Locations API Blueprint - SINGLE SOURCE OF TRUTH
Consolidates all location endpoints into one unified API.
Automatically detects and uses either places_engine (Firebase) or SQLite backend.
All endpoints through: /api/locations
"""
import logging
import time
from typing import Any, Dict, Optional

import requests
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

master_locations_bp = Blueprint('master_locations', __name__)

# Configuration
PLACES_ENGINE_AVAILABLE = False
_places_engine_service = None


def init_places_engine():
    """Initialize places_engine integration"""
    global PLACES_ENGINE_AVAILABLE, _places_engine_service
    try:
        from places_engine.services import SearchService
        _places_engine_service = SearchService(firebase_path="passed_countries")
        PLACES_ENGINE_AVAILABLE = True
        logger.info("✅ Places Engine (Firebase backend) initialized")
    except Exception as e:
        logger.warning(f"⚠️  Places Engine not available: {e} - Using SQLite fallback")
        PLACES_ENGINE_AVAILABLE = False


def get_places_engine():
    """Get places engine service"""
    if _places_engine_service is None:
        init_places_engine()
    return _places_engine_service


def proxy_to_places_engine(endpoint: str, params: Dict = None) -> Dict[str, Any]:
    """
    Proxy request to places_engine API and transform response
    """
    try:
        # Get the service
        service = get_places_engine()
        if not service:
            return None
        
        # Parse the endpoint and params
        # This is a placeholder - in real implementation, we'd call service methods directly
        logger.debug(f"Proxying to places_engine: {endpoint}")
        return None
    except Exception as e:
        logger.error(f"Error proxying to places_engine: {e}")
        return None


# ============================================================================
# COUNTRIES ENDPOINTS
# ============================================================================

@master_locations_bp.route('/countries', methods=['GET'])
def get_countries():
    """Get all countries"""
    try:
        if PLACES_ENGINE_AVAILABLE:
            service = get_places_engine()
            if service:
                # Call places_engine service
                # Note: places_engine might not have a direct "get all" - search instead
                logger.info("Using places_engine backend for countries list")
        
        # Fallback to SQLite
        from ..models import CountriesModel
        countries = CountriesModel.get_all()
        return jsonify({
            'success': True,
            'data': countries,
            'message': f'Retrieved {len(countries)} countries',
            'backend': 'sqlite'
        }), 200
    except Exception as e:
        logger.error(f"Error fetching countries: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve countries',
            'status_code': 500
        }), 500


@master_locations_bp.route('/countries/search', methods=['GET'])
def search_countries():
    """Search countries by name"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'success': False,
                'error': "Search query 'q' is required",
                'status_code': 400
            }), 400
        
        if PLACES_ENGINE_AVAILABLE:
            service = get_places_engine()
            if service:
                try:
                    start_time = time.time()
                    response = service.search_country(query=query)
                    elapsed = time.time() - start_time
                    
                    return jsonify({
                        'success': True,
                        'data': [response.data] if response.data else [],
                        'message': f'Found country: {query}',
                        'backend': 'firebase',
                        'response_time_ms': elapsed * 1000,
                        'metadata': {
                            'firebase_reads': getattr(response.metadata, 'firebase_reads', 0),
                            'cache_hit': getattr(response.metadata, 'cache_hit', False)
                        } if hasattr(response, 'metadata') else {}
                    }), 200
                except Exception as e:
                    logger.warning(f"Places engine search failed: {e}, falling back to SQLite")
        
        # Fallback to SQLite
        from ..models import CountriesModel
        countries = CountriesModel.get_all()
        results = [c for c in countries if query.lower() in c.get('name', '').lower()]
        
        return jsonify({
            'success': True,
            'data': results,
            'message': f"Found {len(results)} countries matching '{query}'",
            'backend': 'sqlite'
        }), 200
    except Exception as e:
        logger.error(f"Error searching countries: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to search countries',
            'status_code': 500
        }), 500


@master_locations_bp.route('/countries/<country_id>', methods=['GET'])
def get_country(country_id: str):
    """Get a specific country by ID"""
    try:
        from ..models import CountriesModel
        country = CountriesModel.get_by_id(country_id)
        
        if not country:
            return jsonify({
                'success': False,
                'error': 'Country not found',
                'status_code': 404
            }), 404
        
        return jsonify({
            'success': True,
            'data': country,
            'message': 'Country retrieved successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error fetching country {country_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve country',
            'status_code': 500
        }), 500


# ============================================================================
# STATES ENDPOINTS
# ============================================================================

@master_locations_bp.route('/countries/<country_id>/states', methods=['GET'])
def get_states_by_country(country_id: str):
    """Get all states in a country"""
    try:
        from ..models import CountriesModel, StatesModel

        # Verify country exists
        country = CountriesModel.get_by_id(country_id)
        if not country:
            return jsonify({
                'success': False,
                'error': 'Country not found',
                'status_code': 404
            }), 404
        
        states = StatesModel.get_by_country(country_id)
        
        return jsonify({
            'success': True,
            'data': states,
            'message': f"Retrieved {len(states)} states for {country.get('name', 'country')}"
        }), 200
    except Exception as e:
        logger.error(f"Error fetching states for {country_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve states',
            'status_code': 500
        }), 500


@master_locations_bp.route('/states/<state_id>', methods=['GET'])
def get_state(state_id: str):
    """Get a specific state by ID"""
    try:
        from ..models import StatesModel
        state = StatesModel.get_by_id(state_id)
        
        if not state:
            return jsonify({
                'success': False,
                'error': 'State not found',
                'status_code': 404
            }), 404
        
        return jsonify({
            'success': True,
            'data': state,
            'message': 'State retrieved successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error fetching state {state_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve state',
            'status_code': 500
        }), 500


# ============================================================================
# CITIES ENDPOINTS
# ============================================================================

@master_locations_bp.route('/countries/<country_id>/cities', methods=['GET'])
def get_cities_by_country(country_id: str):
    """Get all cities in a country"""
    try:
        from ..models import CitiesModel, CountriesModel
        
        country = CountriesModel.get_by_id(country_id)
        if not country:
            return jsonify({
                'success': False,
                'error': 'Country not found',
                'status_code': 404
            }), 404
        
        cities = CitiesModel.get_by_country(country_id)
        
        return jsonify({
            'success': True,
            'data': cities,
            'message': f"Retrieved {len(cities)} cities in {country.get('name', 'country')}"
        }), 200
    except Exception as e:
        logger.error(f"Error fetching cities for {country_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve cities',
            'status_code': 500
        }), 500


@master_locations_bp.route('/states/<state_id>/cities', methods=['GET'])
def get_cities_by_state(state_id: str):
    """Get all cities in a state"""
    try:
        from ..models import CitiesModel, StatesModel
        
        state = StatesModel.get_by_id(state_id)
        if not state:
            return jsonify({
                'success': False,
                'error': 'State not found',
                'status_code': 404
            }), 404
        
        cities = CitiesModel.get_by_state(state_id)
        
        return jsonify({
            'success': True,
            'data': cities,
            'message': f"Retrieved {len(cities)} cities in {state.get('name', 'state')}"
        }), 200
    except Exception as e:
        logger.error(f"Error fetching cities for {state_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve cities',
            'status_code': 500
        }), 500


@master_locations_bp.route('/cities/<city_id>', methods=['GET'])
def get_city(city_id: str):
    """Get a specific city by ID"""
    try:
        from ..models import CitiesModel
        city = CitiesModel.get_by_id(city_id)
        
        if not city:
            return jsonify({
                'success': False,
                'error': 'City not found',
                'status_code': 404
            }), 404
        
        return jsonify({
            'success': True,
            'data': city,
            'message': 'City retrieved successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error fetching city {city_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve city',
            'status_code': 500
        }), 500


@master_locations_bp.route('/cities/search', methods=['GET'])
def search_cities():
    """Search cities by name"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'success': False,
                'error': "Search query 'q' is required",
                'status_code': 400
            }), 400
        
        country_filter = request.args.get('country', '').strip()
        state_filter = request.args.get('state', '').strip()
        
        from ..models import CitiesModel
        all_cities = CitiesModel.get_all()
        
        # Apply filters
        results = [c for c in all_cities if query.lower() in c.get('name', '').lower()]
        
        if country_filter:
            results = [c for c in results if c.get('country_id') == country_filter]
        
        if state_filter:
            results = [c for c in results if c.get('state_id') == state_filter]
        
        return jsonify({
            'success': True,
            'data': results,
            'message': f"Found {len(results)} cities matching '{query}'"
        }), 200
    except Exception as e:
        logger.error(f"Error searching cities: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to search cities',
            'status_code': 500
        }), 500


# ============================================================================
# PLACES ENDPOINTS
# ============================================================================

@master_locations_bp.route('/cities/<city_id>/places', methods=['GET'])
def get_places_by_city(city_id: str):
    """Get all places in a city (paginated)"""
    try:
        from ..models import CitiesModel, PlacesModel
        
        city = CitiesModel.get_by_id(city_id)
        if not city:
            return jsonify({
                'success': False,
                'error': 'City not found',
                'status_code': 404
            }), 404
        
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        
        places = PlacesModel.get_by_city(city_id, limit, offset)
        total = PlacesModel.count_by_city(city_id)
        
        return jsonify({
            'success': True,
            'data': places,
            'message': f"Retrieved {len(places)} places in {city.get('name', 'city')}",
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': total,
                'has_more': (offset + limit) < total
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching places for city {city_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve places',
            'status_code': 500
        }), 500


@master_locations_bp.route('/places/<place_id>', methods=['GET'])
def get_place(place_id: str):
    """Get a specific place by ID"""
    try:
        from ..models import PlacesModel
        place = PlacesModel.get_by_id(place_id)
        
        if not place:
            return jsonify({
                'success': False,
                'error': 'Place not found',
                'status_code': 404
            }), 404
        
        return jsonify({
            'success': True,
            'data': place,
            'message': 'Place retrieved successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error fetching place {place_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve place',
            'status_code': 500
        }), 500


@master_locations_bp.route('/places/search', methods=['GET'])
def search_places():
    """Search places by name"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'success': False,
                'error': "Search query 'q' is required",
                'status_code': 400
            }), 400
        
        city_filter = request.args.get('city', '').strip()
        country_filter = request.args.get('country', '').strip()
        limit = request.args.get('limit', default=50, type=int)
        
        limit = min(max(limit, 1), 100)
        
        from ..models import PlacesModel
        results = PlacesModel.search(query, limit=limit)
        
        if city_filter:
            results = [p for p in results if p.get('city_id') == city_filter]
        
        if country_filter:
            results = [p for p in results if p.get('country_id') == country_filter]
        
        return jsonify({
            'success': True,
            'data': results,
            'message': f"Found {len(results)} places matching '{query}'"
        }), 200
    except Exception as e:
        logger.error(f"Error searching places: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to search places',
            'status_code': 500
        }), 500
