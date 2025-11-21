"""
Countries API routes
Handles all country-related endpoints.
"""
from flask import Blueprint
from ..models import CountriesModel
from ..utils import success_response, not_found_response, error_response
import logging

logger = logging.getLogger(__name__)

countries_bp = Blueprint('countries', __name__)


@countries_bp.route('/', methods=['GET'])
def get_countries():
    """
    Get all countries
    
    Returns:
        200: List of all countries
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


@countries_bp.route('/<country_id>', methods=['GET'])
def get_country(country_id: str):
    """
    Get a specific country by ID
    
    Args:
        country_id: Country identifier
        
    Returns:
        200: Country data
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
