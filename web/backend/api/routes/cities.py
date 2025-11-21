"""
Cities API routes
Handles all city-related endpoints.
"""
from flask import Blueprint
from ..models import CitiesModel, StatesModel, CountriesModel
from ..utils import success_response, not_found_response, error_response
import logging

logger = logging.getLogger(__name__)

cities_bp = Blueprint('cities', __name__)


@cities_bp.route('/<city_id>', methods=['GET'])
def get_city(city_id: str):
    """
    Get a specific city by ID
    
    Args:
        city_id: City identifier
        
    Returns:
        200: City data
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


@cities_bp.route('/state/<state_id>', methods=['GET'])
def get_cities_by_state(state_id: str):
    """
    Get all cities in a state
    
    Args:
        state_id: State identifier
        
    Returns:
        200: List of cities
        404: State not found
        500: Internal server error
    """
    try:
        # Verify state exists
        state = StatesModel.get_by_id(state_id)
        if not state:
            return not_found_response("State")
        
        cities = CitiesModel.get_by_state(state_id)
        
        return success_response(
            data=cities,
            message=f"Retrieved {len(cities)} cities"
        )
    except Exception as e:
        logger.error(f"Error fetching cities for state {state_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve cities",
            status_code=500
        )


@cities_bp.route('/country/<country_id>', methods=['GET'])
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
        # Verify country exists
        country = CountriesModel.get_by_id(country_id)
        if not country:
            return not_found_response("Country")
        
        cities = CitiesModel.get_by_country(country_id)
        
        return success_response(
            data=cities,
            message=f"Retrieved {len(cities)} cities"
        )
    except Exception as e:
        logger.error(f"Error fetching cities for country {country_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve cities",
            status_code=500
        )
