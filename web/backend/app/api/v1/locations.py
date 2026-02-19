"""
Locations API routes (Unified)
Consolidated endpoints for countries, states, cities, and places.
Replaces fragmented location endpoints with a clean, hierarchical structure.
"""
import logging

from app.api.utils import error_response, not_found_response, success_response
from app.domain.places.location_models import (CitiesModel, CountriesModel,
                                               PlacesModel, StatesModel)
from app.infrastructure.cache.redis import cache_response as cached
from flask import Blueprint, request

logger = logging.getLogger(__name__)

locations_bp = Blueprint('locations', __name__)


# ============================================================================
# UNIFIED SEARCH ENDPOINT
# ============================================================================

@locations_bp.route('/search', methods=['GET'])
@cached('locations:search', ttl=300)
def unified_search():
    """
    Unified search across countries, states, cities and places
    Query: ?q=<search_term>&limit=20&page=1
    
    Returns:
        - For country match: match_type='country' with sections containing states and their top places
        - For state match: match_type='state' with places array
        - For city match: match_type='city' with places array
    """
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return error_response(
                message="Search query 'q' is required",
                status_code=400
            )
        
        limit = request.args.get('limit', default=20, type=int)
        page = request.args.get('page', default=1, type=int)
        limit = min(max(limit, 1), 100)
        page = max(page, 1)
        offset = (page - 1) * limit
        
        query_lower = query.lower()
        
        # Get all reference data
        try:
            countries = CountriesModel.get_all()
            states = StatesModel.get_all()
            cities = CitiesModel.get_all()
        except RuntimeError as e:
            logger.warning("Database not initialized for location search: %s", e)
            return success_response(
                data={'places': [], 'count': 0, 'match_type': 'none'},
                message="Location search unavailable - database not initialized"
            )
        
        # Build lookup dictionaries
        country_lookup = {c.get('id'): c for c in countries}
        state_lookup = {s.get('id'): s for s in states}
        # city_lookup used for state/country references in matched cities
        _city_lookup = {c.get('id'): c for c in cities}
        
        # PRIORITY ORDER: exact city > exact state > exact country > partial city > partial state > partial country
        
        # 1. Check for EXACT CITY match first (highest priority)
        matched_city = None
        for city in cities:
            if city.get('name', '').lower() == query_lower:
                matched_city = city
                break
        
        if matched_city:
            city_id = str(matched_city.get('id', ''))
            state = state_lookup.get(matched_city.get('state_id'), {})
            country = country_lookup.get(matched_city.get('country_id'), {})
            
            # Get places for this city
            places = PlacesModel.get_by_city(city_id, limit=limit, offset=offset)
            
            return success_response(
                data={
                    'match_type': 'city',
                    'matched': {
                        'id': matched_city.get('id'),
                        'name': matched_city.get('name'),
                        'state': state.get('name', ''),
                        'country': country.get('name', '')
                    },
                    'places': places,
                    'count': len(places),
                    'cache_hit': False,
                    'firebase_reads': 0,
                    'response_time_ms': 0
                },
                message=f"Found {len(places)} places in {matched_city.get('name')}"
            )
        
        # 2. Check for EXACT STATE match
        matched_state = None
        for state in states:
            if state.get('name', '').lower() == query_lower:
                matched_state = state
                break
        
        if matched_state:
            state_id = str(matched_state.get('id', ''))
            country = country_lookup.get(matched_state.get('country_id'), {})
            
            # Get places for this state
            places = PlacesModel.get_by_state(state_id, limit=limit, offset=offset)
            
            return success_response(
                data={
                    'match_type': 'state',
                    'matched': {
                        'id': matched_state.get('id'),
                        'name': matched_state.get('name'),
                        'country': country.get('name', '')
                    },
                    'places': places,
                    'count': len(places),
                    'cache_hit': False,
                    'firebase_reads': 0,
                    'response_time_ms': 0
                },
                message=f"Found {len(places)} places in {matched_state.get('name')}"
            )
        
        # 3. Check for EXACT COUNTRY match
        matched_country = None
        for country in countries:
            if country.get('name', '').lower() == query_lower:
                matched_country = country
                break
        
        if matched_country:
            # Get all states in this country with top 5 places each
            country_states = [s for s in states if s.get('country_id') == matched_country.get('id')]
            
            sections = []
            total_places = 0
            
            for state in country_states[:10]:  # Limit to 10 states
                state_id = str(state.get('id', ''))
                # Get top 5 places for this state
                places = PlacesModel.get_by_state(state_id, limit=5, offset=0)
                
                if places:
                    sections.append({
                        'state_id': state_id,
                        'state_name': state.get('name', ''),
                        'state_slug': state.get('slug', state.get('name', '').lower().replace(' ', '-')),
                        'place_count': len(places),
                        'top_places': places
                    })
                    total_places += len(places)
            
            return success_response(
                data={
                    'match_type': 'country',
                    'matched': {
                        'id': matched_country.get('id'),
                        'name': matched_country.get('name'),
                        'state_count': len(country_states)
                    },
                    'sections': sections,
                    'state_count': len(sections),
                    'count': total_places,
                    'cache_hit': False,
                    'firebase_reads': 0,
                    'response_time_ms': 0
                },
                message=f"Found {total_places} places in {len(sections)} states of {matched_country.get('name')}"
            )
        
        # 4. Check for PARTIAL CITY match
        for city in cities:
            if query_lower in city.get('name', '').lower():
                matched_city = city
                break
        
        if matched_city:
            city_id = str(matched_city.get('id', ''))
            state = state_lookup.get(matched_city.get('state_id'), {})
            country = country_lookup.get(matched_city.get('country_id'), {})
            
            places = PlacesModel.get_by_city(city_id, limit=limit, offset=offset)
            
            return success_response(
                data={
                    'match_type': 'city',
                    'matched': {
                        'id': matched_city.get('id'),
                        'name': matched_city.get('name'),
                        'state': state.get('name', ''),
                        'country': country.get('name', '')
                    },
                    'places': places,
                    'count': len(places),
                    'cache_hit': False,
                    'firebase_reads': 0,
                    'response_time_ms': 0
                },
                message=f"Found {len(places)} places in {matched_city.get('name')}"
            )
        
        # 5. Check for PARTIAL STATE match
        for state in states:
            if query_lower in state.get('name', '').lower():
                matched_state = state
                break
        
        if matched_state:
            state_id = str(matched_state.get('id', ''))
            country = country_lookup.get(matched_state.get('country_id'), {})
            
            places = PlacesModel.get_by_state(state_id, limit=limit, offset=offset)
            
            return success_response(
                data={
                    'match_type': 'state',
                    'matched': {
                        'id': matched_state.get('id'),
                        'name': matched_state.get('name'),
                        'country': country.get('name', '')
                    },
                    'places': places,
                    'count': len(places),
                    'cache_hit': False,
                    'firebase_reads': 0,
                    'response_time_ms': 0
                },
                message=f"Found {len(places)} places in {matched_state.get('name')}"
            )
        
        # 6. Check for PARTIAL COUNTRY match
        for country in countries:
            if query_lower in country.get('name', '').lower():
                matched_country = country
                break
        
        if matched_country:
            country_states = [s for s in states if s.get('country_id') == matched_country.get('id')]
            
            sections = []
            total_places = 0
            
            for state in country_states[:10]:
                state_id = str(state.get('id', ''))
                places = PlacesModel.get_by_state(state_id, limit=5, offset=0)
                
                if places:
                    sections.append({
                        'state_id': state_id,
                        'state_name': state.get('name', ''),
                        'state_slug': state.get('slug', state.get('name', '').lower().replace(' ', '-')),
                        'place_count': len(places),
                        'top_places': places
                    })
                    total_places += len(places)
            
            return success_response(
                data={
                    'match_type': 'country',
                    'matched': {
                        'id': matched_country.get('id'),
                        'name': matched_country.get('name'),
                        'state_count': len(country_states)
                    },
                    'sections': sections,
                    'state_count': len(sections),
                    'count': total_places,
                    'cache_hit': False,
                    'firebase_reads': 0,
                    'response_time_ms': 0
                },
                message=f"Found {total_places} places in {len(sections)} states of {matched_country.get('name')}"
            )
        
        # 7. No location match found - search places by name
        places = PlacesModel.search_by_name(query, limit=limit, offset=offset)
        
        if places:
            return success_response(
                data={
                    'match_type': 'place',
                    'matched': {
                        'name': query
                    },
                    'places': places,
                    'count': len(places),
                    'cache_hit': False,
                    'firebase_reads': 0,
                    'response_time_ms': 0
                },
                message=f"Found {len(places)} places matching '{query}'"
            )
        
        # Nothing found
        return success_response(
            data={
                'match_type': 'none',
                'matched': None,
                'places': [],
                'count': 0
            },
            message=f"No locations or places found matching '{query}'"
        )
    except (RuntimeError, ValueError, KeyError) as e:
        logger.error("Error in unified search: %s", e, exc_info=True)
        return error_response(
            message="Failed to search locations",
            status_code=500
        )


# ============================================================================
# COUNTRIES ENDPOINTS
# ============================================================================

@locations_bp.route('/countries', methods=['GET'])
@cached('locations:countries', ttl=3600)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error fetching countries: %s", e, exc_info=True)
        return error_response(
            message="Failed to retrieve countries",
            status_code=500
        )


@locations_bp.route('/countries/<country_id>', methods=['GET'])
@cached('locations:country', ttl=3600)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error fetching country %s: %s", country_id, e, exc_info=True)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error searching countries: %s", e, exc_info=True)
        return error_response(
            message="Failed to search countries",
            status_code=500
        )


# ============================================================================
# STATES ENDPOINTS
# ============================================================================

@locations_bp.route('/countries/<country_id>/states', methods=['GET'])
@cached('locations:states', ttl=3600)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error fetching states for %s: %s", country_id, e, exc_info=True)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error fetching state %s: %s", state_id, e, exc_info=True)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error fetching cities for %s: %s", country_id, e, exc_info=True)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error fetching cities for %s: %s", state_id, e, exc_info=True)
        return error_response(
            message="Failed to retrieve cities",
            status_code=500
        )


@locations_bp.route('/cities/<city_id>', methods=['GET'])
@cached('locations:city', ttl=1800)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error fetching city %s: %s", city_id, e, exc_info=True)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error searching cities: %s", e, exc_info=True)
        return error_response(
            message="Failed to search cities",
            status_code=500
        )


# ============================================================================
# PLACES ENDPOINTS
# ============================================================================

@locations_bp.route('/cities/<city_id>/places', methods=['GET'])
@cached('locations:city_places', ttl=300)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error fetching places for city %s: %s", city_id, e, exc_info=True)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error fetching place %s: %s", place_id, e, exc_info=True)
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
    except (RuntimeError, ValueError) as e:
        logger.error("Error searching places: %s", e, exc_info=True)
        return error_response(
            message="Failed to search places",
            status_code=500
        )


# ============================================================================
# AUTOCOMPLETE / DESTINATION SEARCH
# ============================================================================

@locations_bp.route('/autocomplete', methods=['GET'])
@cached('locations:autocomplete', ttl=300)
def autocomplete_destinations():
    """
    Autocomplete search across countries, states, and cities
    Returns a unified list of destinations with coordinates for map centering
    
    Query: ?q=<search_term>&limit=10
    
    Returns:
        200: List of matching destinations with type, name, coordinates
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
        
        limit = request.args.get('limit', default=10, type=int)
        limit = min(max(limit, 1), 50)
        
        results = []
        
        # Search countries using the model
        countries = CountriesModel.get_all()
        query_lower = query.lower()
        for country in countries:
            if query_lower in country.get('name', '').lower():
                results.append({
                    'id': country.get('id'),
                    'type': 'country',
                    'name': country.get('name', ''),
                    'display_name': country.get('name', ''),
                    'coordinates': {
                        'lat': country.get('latitude'),
                        'lng': country.get('longitude')
                    },
                    'country_id': country.get('id'),
                    'country_name': country.get('name', '')
                })
        
        # Search states using the model
        states = StatesModel.get_all()
        for state in states:
            if query_lower in state.get('name', '').lower():
                # Get country name
                country_id = state.get('country_id')
                country_name = ''
                for c in countries:
                    if c.get('id') == country_id:
                        country_name = c.get('name', '')
                        break
                
                results.append({
                    'id': state.get('id'),
                    'type': 'state',
                    'name': state.get('name', ''),
                    'display_name': f"{state.get('name', '')}, {country_name}" if country_name else state.get('name', ''),
                    'coordinates': {
                        'lat': state.get('latitude'),
                        'lng': state.get('longitude')
                    },
                    'country_id': state.get('country_id'),
                    'country_name': country_name,
                    'state_id': state.get('id'),
                    'state_name': state.get('name', '')
                })
        
        # Search cities using the model
        cities = CitiesModel.get_all()
        for city in cities:
            if query_lower in city.get('name', '').lower():
                # Get state and country names
                state_id = city.get('state_id')
                state_name = ''
                for s in states:
                    if s.get('id') == state_id:
                        state_name = s.get('name', '')
                        break
                
                country_id = city.get('country_id')
                country_name = ''
                for c in countries:
                    if c.get('id') == country_id:
                        country_name = c.get('name', '')
                        break
                
                # Build display name: City, State, Country (skip duplicate names)
                city_name = city.get('name', '')
                parts = [city_name]
                # Only add state if different from city name
                if state_name and state_name.lower() != city_name.lower():
                    parts.append(state_name)
                if country_name:
                    parts.append(country_name)
                display_name = ', '.join(parts)
                
                results.append({
                    'id': city.get('id'),
                    'type': 'city',
                    'name': city.get('name', ''),
                    'display_name': display_name,
                    'coordinates': {
                        'lat': city.get('latitude'),
                        'lng': city.get('longitude')
                    },
                    'country_id': city.get('country_id'),
                    'country_name': country_name,
                    'state_id': city.get('state_id'),
                    'state_name': state_name,
                    'city_id': city.get('id'),
                    'city_name': city.get('name', '')
                })
        
        # Search places (individual tourist attractions) - use simple name search
        try:
            from app.domain.places.location_repository import get_db
            places_query = """
                SELECT p.id, p.place_name, p.name_english, p.latitude, p.longitude, 
                       p.city_id, ci.state_id, s.country_id,
                       ci.city_name, s.state_name, co.country_name
                FROM places p
                LEFT JOIN cities ci ON p.city_id = ci.id
                LEFT JOIN states s ON ci.state_id = s.id
                LEFT JOIN countries co ON s.country_id = co.id
                WHERE LOWER(p.place_name) LIKE ? OR LOWER(p.name_english) LIKE ?
                ORDER BY p.rating_tourist_priority DESC
                LIMIT 10
            """
            places_results = get_db().execute_query(places_query, (f'%{query_lower}%', f'%{query_lower}%'))
            for place in (places_results or []):
                # Use name_english if available, otherwise place_name
                place_display = place.get('name_english') or place.get('place_name', '')
                results.append({
                    'id': place.get('id'),
                    'type': 'place',
                    'name': place_display,
                    'display_name': f"{place_display}, {place.get('city_name') or ''}, {place.get('country_name') or ''}".strip(', '),
                    'coordinates': {
                        'lat': place.get('latitude'),
                        'lng': place.get('longitude')
                    },
                    'country_id': place.get('country_id'),
                    'country_name': place.get('country_name', ''),
                    'state_id': place.get('state_id'),
                    'state_name': place.get('state_name', ''),
                    'city_id': place.get('city_id'),
                    'city_name': place.get('city_name', ''),
                    'place_id': place.get('id')
                })
        except (RuntimeError, ValueError) as place_err:
            logger.warning("Places search failed in autocomplete: %s", place_err)
        
        # Sort by relevance (exact match first, then starts with, then contains)
        # Priority: exact match > starts with > contains
        # Type priority within same relevance: city > state > country > place
        def sort_key(item):
            name_lower = item['name'].lower()
            type_priority = {'city': 0, 'state': 1, 'country': 2, 'place': 3}
            type_order = type_priority.get(item['type'], 4)
            
            if name_lower == query_lower:
                return (0, type_order, item['name'])
            elif name_lower.startswith(query_lower):
                return (1, type_order, item['name'])
            else:
                return (2, type_order, item['name'])
        
        results.sort(key=sort_key)
        
        # Remove duplicates by display_name (the full name shown to user)
        # This prevents "Jaipur, India" showing twice (as city and state)
        # Priority: city > state > country > place (already sorted above)
        seen_display_names = set()
        unique_results = []
        for r in results:
            display_key = r['display_name'].lower().strip()
            if display_key not in seen_display_names:
                seen_display_names.add(display_key)
                unique_results.append(r)
        
        results = unique_results[:limit]
        
        return success_response(
            data=results,
            message=f"Found {len(results)} destinations matching '{query}'"
        )
    except (RuntimeError, ValueError, KeyError) as e:
        logger.error("Error in autocomplete: %s", e, exc_info=True)
        return error_response(
            message="Failed to search destinations",
            status_code=500
        )


@locations_bp.route('/suggested-places', methods=['GET'])
@cached('locations:suggested', ttl=300)
def get_suggested_places():
    """
    Get suggested places for a destination (country, state, or city)
    Query: ?type=<country|state|city>&id=<destination_id>&limit=10
    
    Returns:
        200: List of suggested places with coordinates
        400: Missing required parameters
        500: Internal server error
    """
    try:
        dest_type = request.args.get('type', '').strip().lower()
        dest_id = request.args.get('id', '').strip()
        limit = request.args.get('limit', default=10, type=int)
        
        if not dest_type or not dest_id:
            return error_response(
                message="Both 'type' and 'id' parameters are required",
                status_code=400
            )
        
        if dest_type not in ['country', 'state', 'city']:
            return error_response(
                message="Type must be 'country', 'state', or 'city'",
                status_code=400
            )
        
        limit = min(max(limit, 1), 50)
        places = []
        
        if dest_type == 'city':
            places = PlacesModel.get_by_city(dest_id, limit, 0)
        elif dest_type == 'state':
            places = PlacesModel.get_by_state(dest_id, limit, 0)
        elif dest_type == 'country':
            places = PlacesModel.get_by_country(dest_id, limit, 0)
        
        # Transform to simplified format for frontend
        suggested = []
        for place in places:
            coords = place.get('coordinates', {})
            lat = coords.get('lat') if isinstance(coords, dict) else None
            lng = coords.get('lng') if isinstance(coords, dict) else None
            
            suggested.append({
                'id': place.get('id'),
                'name': place.get('name', ''),
                'hint': place.get('summary', '')[:100] if place.get('summary') else '',
                'category': place.get('category', ''),
                'rating': place.get('rating'),
                'coordinates': {
                    'lat': lat,
                    'lng': lng
                },
                'city_name': place.get('city_name', ''),
                'country_name': place.get('country_name', ''),
                'photos': place.get('photos', [])[:1] if place.get('photos') else []
            })
        
        return success_response(
            data=suggested,
            message=f"Found {len(suggested)} suggested places"
        )
    except (RuntimeError, ValueError) as e:
        logger.error("Error getting suggested places: %s", e, exc_info=True)
        return error_response(
            message="Failed to get suggested places",
            status_code=500
        )