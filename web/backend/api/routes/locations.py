"""
Locations API routes (Unified)
Consolidated endpoints for countries, states, cities, and places.
Replaces fragmented location endpoints with a clean, hierarchical structure.
"""
import logging

from flask import Blueprint, request

from ..models import CitiesModel, CountriesModel, PlacesModel, StatesModel
from ..utils import error_response, not_found_response, success_response

logger = logging.getLogger(__name__)

locations_bp = Blueprint('locations', __name__)


# ============================================================================
# COUNTRIES ENDPOINTS
# ============================================================================

@locations_bp.route('/countries', methods=['GET'])
def get_countries():
    """
    Get all countries
    
    Returns:
        200: List of all countries with basic info
        500: Internal server error
    """
    try:
        countries = CountriesModel.get_all()
        return success_response(
            data=countries,
            message=f"Retrieved {len(countries)} countries"
        )
    except Exception as e:
        logger.error(f"Error fetching countries: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve countries",
            status_code=500
        )


@locations_bp.route('/countries/<country_id>', methods=['GET'])
def get_country(country_id: str):
    """
    Get a specific country by ID
    
    Args:
        country_id: Country identifier (ISO code or internal ID)
        
    Returns:
        200: Country data with metadata
        404: Country not found
        500: Internal server error
    """
    try:
        country = CountriesModel.get_by_id(country_id)
        
        if not country:
            return not_found_response("Country")
        
        return success_response(
            data=country,
            message="Country retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error fetching country {country_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve country",
            status_code=500
        )


@locations_bp.route('/countries/search', methods=['GET'])
def search_countries():
    """
    Search countries by name
    Query: ?q=<search_term>
    
    Returns:
        200: List of matching countries
        400: Missing search query
        500: Internal server error
    """
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return error_response(
                message="Search query 'q' is required",
                status_code=400
            )
        
        countries = CountriesModel.get_all()
        
        # Simple search by name
        results = [
            c for c in countries 
            if query.lower() in c.get('name', '').lower()
        ]
        
        return success_response(
            data=results,
            message=f"Found {len(results)} countries matching '{query}'"
        )
    except Exception as e:
        logger.error(f"Error searching countries: {e}", exc_info=True)
        return error_response(
            message="Failed to search countries",
            status_code=500
        )


# ============================================================================
# STATES ENDPOINTS
# ============================================================================

@locations_bp.route('/countries/<country_id>/states', methods=['GET'])
def get_states_by_country(country_id: str):
    """
    Get all states/provinces in a country
    
    Args:
        country_id: Country identifier
        
    Returns:
        200: List of states in the country
        404: Country not found
        500: Internal server error
    """
    try:
        # Verify country exists
        country = CountriesModel.get_by_id(country_id)
        if not country:
            return not_found_response("Country")
        
        states = StatesModel.get_by_country(country_id)
        
        return success_response(
            data=states,
            message=f"Retrieved {len(states)} states for {country.get('name', 'country')}"
        )
    except Exception as e:
        logger.error(f"Error fetching states for {country_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve states",
            status_code=500
        )


@locations_bp.route('/states/<state_id>', methods=['GET'])
def get_state(state_id: str):
    """
    Get a specific state by ID
    
    Args:
        state_id: State identifier
        
    Returns:
        200: State data with country reference
        404: State not found
        500: Internal server error
    """
    try:
        state = StatesModel.get_by_id(state_id)
        
        if not state:
            return not_found_response("State")
        
        return success_response(
            data=state,
            message="State retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error fetching state {state_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve state",
            status_code=500
        )


# ============================================================================
# CITIES ENDPOINTS
# ============================================================================

@locations_bp.route('/countries/<country_id>/cities', methods=['GET'])
def get_cities_by_country(country_id: str):
    """
    Get all cities in a country
    
    Args:
        country_id: Country identifier
        
    Returns:
        200: List of cities
        404: Country not found
        500: Internal server error
    """
    try:
        country = CountriesModel.get_by_id(country_id)
        if not country:
            return not_found_response("Country")
        
        cities = CitiesModel.get_by_country(country_id)
        
        return success_response(
            data=cities,
            message=f"Retrieved {len(cities)} cities in {country.get('name', 'country')}"
        )
    except Exception as e:
        logger.error(f"Error fetching cities for {country_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve cities",
            status_code=500
        )


@locations_bp.route('/states/<state_id>/cities', methods=['GET'])
def get_cities_by_state(state_id: str):
    """
    Get all cities in a state
    
    Args:
        state_id: State identifier
        
    Returns:
        200: List of cities in the state
        404: State not found
        500: Internal server error
    """
    try:
        state = StatesModel.get_by_id(state_id)
        if not state:
            return not_found_response("State")
        
        cities = CitiesModel.get_by_state(state_id)
        
        return success_response(
            data=cities,
            message=f"Retrieved {len(cities)} cities in {state.get('name', 'state')}"
        )
    except Exception as e:
        logger.error(f"Error fetching cities for {state_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve cities",
            status_code=500
        )


@locations_bp.route('/cities/<city_id>', methods=['GET'])
def get_city(city_id: str):
    """
    Get a specific city by ID
    
    Args:
        city_id: City identifier
        
    Returns:
        200: City data with state and country references
        404: City not found
        500: Internal server error
    """
    try:
        city = CitiesModel.get_by_id(city_id)
        
        if not city:
            return not_found_response("City")
        
        return success_response(
            data=city,
            message="City retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error fetching city {city_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve city",
            status_code=500
        )


@locations_bp.route('/cities/search', methods=['GET'])
def search_cities():
    """
    Search cities by name
    Query: ?q=<search_term>&country=<country_id>&state=<state_id>
    
    Returns:
        200: List of matching cities
        400: Missing search query
        500: Internal server error
    """
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return error_response(
                message="Search query 'q' is required",
                status_code=400
            )
        
        country_filter = request.args.get('country', '').strip()
        state_filter = request.args.get('state', '').strip()
        
        all_cities = CitiesModel.get_all()
        
        # Apply filters
        results = [
            c for c in all_cities
            if query.lower() in c.get('name', '').lower()
        ]
        
        if country_filter:
            results = [c for c in results if c.get('country_id') == country_filter]
        
        if state_filter:
            results = [c for c in results if c.get('state_id') == state_filter]
        
        return success_response(
            data=results,
            message=f"Found {len(results)} cities matching '{query}'"
        )
    except Exception as e:
        logger.error(f"Error searching cities: {e}", exc_info=True)
        return error_response(
            message="Failed to search cities",
            status_code=500
        )


# ============================================================================
# PLACES ENDPOINTS
# ============================================================================

@locations_bp.route('/cities/<city_id>/places', methods=['GET'])
def get_places_by_city(city_id: str):
    """
    Get all places in a city
    Query: ?limit=50&offset=0
    
    Args:
        city_id: City identifier
        
    Returns:
        200: List of places with pagination metadata
        404: City not found
        500: Internal server error
    """
    try:
        city = CitiesModel.get_by_id(city_id)
        if not city:
            return not_found_response("City")
        
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        # Validate limits
        limit = min(max(limit, 1), 100)  # 1-100
        offset = max(offset, 0)
        
        places = PlacesModel.get_by_city(city_id, limit, offset)
        total = PlacesModel.count_by_city(city_id)
        
        return success_response(
            data=places,
            message=f"Retrieved {len(places)} places in {city.get('name', 'city')}",
            pagination={
                'limit': limit,
                'offset': offset,
                'total': total,
                'has_more': (offset + limit) < total
            }
        )
    except Exception as e:
        logger.error(f"Error fetching places for city {city_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve places",
            status_code=500
        )


@locations_bp.route('/places/<place_id>', methods=['GET'])
def get_place(place_id: str):
    """
    Get a specific place by ID
    
    Args:
        place_id: Place identifier
        
    Returns:
        200: Place data with full details
        404: Place not found
        500: Internal server error
    """
    try:
        place = PlacesModel.get_by_id(place_id)
        
        if not place:
            return not_found_response("Place")
        
        return success_response(
            data=place,
            message="Place retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error fetching place {place_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve place",
            status_code=500
        )


@locations_bp.route('/places/search', methods=['GET'])
def search_places():
    """
    Search places by name
    Query: ?q=<search_term>&city=<city_id>&country=<country_id>
    
    Returns:
        200: List of matching places
        400: Missing search query
        500: Internal server error
    """
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return error_response(
                message="Search query 'q' is required",
                status_code=400
            )
        
        city_filter = request.args.get('city', '').strip()
        country_filter = request.args.get('country', '').strip()
        limit = request.args.get('limit', default=50, type=int)
        
        limit = min(max(limit, 1), 100)
        
        # Perform search
        results = PlacesModel.search(query, limit=limit)
        
        # Apply filters
        if city_filter:
            results = [p for p in results if p.get('city_id') == city_filter]
        
        if country_filter:
            results = [p for p in results if p.get('country_id') == country_filter]
        
        return success_response(
            data=results,
            message=f"Found {len(results)} places matching '{query}'"
        )
    except Exception as e:
        logger.error(f"Error searching places: {e}", exc_info=True)
        return error_response(
            message="Failed to search places",
            status_code=500
        )
