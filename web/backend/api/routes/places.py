"""
Places API routes
Handles all place-related endpoints including search.
"""
from flask import Blueprint, request
from ..models import PlacesModel, CitiesModel, StatesModel, CountriesModel
from ..utils import (
    success_response,
    error_response,
    not_found_response,
    paginated_response,
    validate_pagination,
    validate_search_query
)
import logging

logger = logging.getLogger(__name__)

places_bp = Blueprint('places', __name__)


@places_bp.route('/<place_id>', methods=['GET'])
def get_place(place_id: str):
    """
    Get a specific place by ID
    
    Args:
        place_id: Place identifier
        
    Returns:
        200: Place data
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


@places_bp.route('/city/<city_id>', methods=['GET'])
def get_places_by_city(city_id: str):
    """
    Get all places in a city with pagination
    
    Args:
        city_id: City identifier
        
    Query Parameters:
        limit: Maximum results (default: 50, max: 100)
        offset: Pagination offset (default: 0)
        
    Returns:
        200: Paginated list of places
        404: City not found
        500: Internal server error
    """
    try:
        # Verify city exists
        city = CitiesModel.get_by_id(city_id)
        if not city:
            return not_found_response("City")
        
        # Get pagination params
        limit, offset = validate_pagination(max_limit=100)
        
        # Get places
        places = PlacesModel.get_by_city(city_id, limit, offset)
        total = PlacesModel.count_by_city(city_id)
        
        return paginated_response(
            data=places,
            total=total,
            limit=limit,
            offset=offset,
            message=f"Retrieved places for {city['name']}"
        )
    except Exception as e:
        logger.error(f"Error fetching places for city {city_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve places",
            status_code=500
        )


@places_bp.route('/state/<state_id>', methods=['GET'])
def get_places_by_state(state_id: str):
    """
    Get all places in a state (without city) with pagination
    
    Args:
        state_id: State identifier
        
    Query Parameters:
        limit: Maximum results (default: 50, max: 100)
        offset: Pagination offset (default: 0)
        
    Returns:
        200: Paginated list of places
        404: State not found
        500: Internal server error
    """
    try:
        # Verify state exists
        state = StatesModel.get_by_id(state_id)
        if not state:
            return not_found_response("State")
        
        # Get pagination params
        limit, offset = validate_pagination(max_limit=100)
        
        # Get places
        places = PlacesModel.get_by_state(state_id, limit, offset)
        total = PlacesModel.count_by_state(state_id)
        
        return paginated_response(
            data=places,
            total=total,
            limit=limit,
            offset=offset,
            message=f"Retrieved places for {state['name']}"
        )
    except Exception as e:
        logger.error(f"Error fetching places for state {state_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve places",
            status_code=500
        )


@places_bp.route('/country/<country_id>', methods=['GET'])
def get_places_by_country(country_id: str):
    """
    Get all places in a country with pagination
    
    Args:
        country_id: Country identifier
        
    Query Parameters:
        limit: Maximum results (default: 50, max: 100)
        offset: Pagination offset (default: 0)
        
    Returns:
        200: Paginated list of places
        404: Country not found
        500: Internal server error
    """
    try:
        # Verify country exists
        country = CountriesModel.get_by_id(country_id)
        if not country:
            return not_found_response("Country")
        
        # Get pagination params
        limit, offset = validate_pagination(max_limit=100)
        
        # Get places
        places = PlacesModel.get_by_country(country_id, limit, offset)
        total = PlacesModel.count_by_country(country_id)
        
        return paginated_response(
            data=places,
            total=total,
            limit=limit,
            offset=offset,
            message=f"Retrieved places for {country['name']}"
        )
    except Exception as e:
        logger.error(f"Error fetching places for country {country_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve places",
            status_code=500
        )


@places_bp.route('/search', methods=['GET'])
def search_places():
    """
    Universal search for places
    
    Query Parameters:
        q: Search query (required, min 2 chars)
        limit: Maximum results (default: 50, max: 100)
        offset: Pagination offset (default: 0)
        
    Returns:
        200: Paginated search results
        400: Invalid query
        500: Internal server error
    """
    try:
        # Validate search query
        try:
            query = validate_search_query(min_length=2, max_length=100)
        except ValueError as e:
            return error_response(message=str(e), status_code=400)
        
        # Get pagination params
        limit, offset = validate_pagination(max_limit=100)
        
        # Search places
        places = PlacesModel.search(query, limit, offset)
        total = PlacesModel.count_search(query)
        
        return paginated_response(
            data=places,
            total=total,
            limit=limit,
            offset=offset,
            message=f"Found {total} results for '{query}'"
        )
    except Exception as e:
        logger.error(f"Error searching places: {e}", exc_info=True)
        return error_response(
            message="Search failed",
            status_code=500
        )
