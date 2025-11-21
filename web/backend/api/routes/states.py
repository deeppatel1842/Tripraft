"""
States API routes
Handles all state-related endpoints.
"""
from flask import Blueprint
from ..models import StatesModel, CountriesModel
from ..utils import success_response, not_found_response, error_response
import logging

logger = logging.getLogger(__name__)

states_bp = Blueprint('states', __name__)


@states_bp.route('/<state_id>', methods=['GET'])
def get_state(state_id: str):
    """
    Get a specific state by ID
    
    Args:
        state_id: State identifier
        
    Returns:
        200: State data
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


@states_bp.route('/country/<country_id>', methods=['GET'])
def get_states_by_country(country_id: str):
    """
    Get all states in a country
    
    Args:
        country_id: Country identifier
        
    Returns:
        200: List of states
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
            message=f"Retrieved {len(states)} states"
        )
    except Exception as e:
        logger.error(f"Error fetching states for country {country_id}: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve states",
            status_code=500
        )
