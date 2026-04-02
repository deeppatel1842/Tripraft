"""
Place Routes for Group Planner
Flask API routes for place operations
"""

import logging

from app.api.utils.responses import (created_response, error_response,
                                     not_found_response, success_response,
                                     validation_error_response)
from app.api.utils.validators import validate_schema
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import require_auth, require_group_role
from app.infrastructure.cache.redis import cache_response, invalidate_cache
from app.schemas.common import AddPlaceSchema, validate_request
from app.schemas.gp_places import (GeocodeSchema, UpdatePlaceRemarksSchema,
                                   UpdatePlaceSchema)
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

# Create Blueprint
places_bp = Blueprint(
    'gp_places',  # Unique name for Group Planner
    __name__,
    url_prefix='/api/v1/group-planner'
)


# =========================================================================
# PLACE ENDPOINTS
# =========================================================================

@places_bp.route('/groups/<group_id>/places', methods=['POST', 'OPTIONS'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
@require_group_role('member')
def add_place(group_id):
    """
    Add a place to the group
    
    Request:
        POST /api/v2/group-planner/groups/<group_id>/places
        Headers: Authorization: Bearer <token>
        Body: {
            "name": "Tokyo Tower",
            "description": "Iconic landmark",
            "address": "Tokyo, Japan",
            "category": "attraction"
        }
    """
    if request.method == 'OPTIONS':
        return success_response()
    
    try:
        from app.services.travel_place_service import place_service
        
        data = request.get_json()
        
        if not data:
            return error_response('Request body required')
        
        validated, errors = validate_request(AddPlaceSchema, data)
        if errors:
            return validation_error_response(errors)
        
        success, result = place_service.add_place(
            group_id=group_id,
            user_id=g.user_id,
            name=validated['name'],
            description=validated.get('description'),
            address=validated.get('address'),
            latitude=validated.get('latitude'),
            longitude=validated.get('longitude'),
            category=validated.get('category'),
            visit_date=validated.get('visit_date'),
            suggested_duration=validated.get('suggested_duration'),
            photo_url=validated.get('photo_url'),
            website=validated.get('website'),
            rating=validated.get('rating')
        )
        
        if success:
            logger.info(f"Place added to group {group_id}")
            invalidate_cache('gp_places:*')
            invalidate_cache('gp_groups:*')
            return created_response(data=result.get('place'))
        else:
            status = 409 if result.get('code') == 'PLACE_ALREADY_EXISTS' else 400
            return error_response(result.get('error'), status)
            
    except Exception as e:
        logger.error(f"Add place error: {str(e)}")
        return error_response('Failed to add place', 500)


@places_bp.route('/groups/<group_id>/places', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_places:list', ttl=Config.CACHE_TTLS['group_list'], vary_on_user=True)
def get_places(group_id):
    """
    Get places for a group (paginated)
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/places?page=1&per_page=20
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_place_service import place_service
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', Config.GP_DEFAULT_LIMIT, type=int), 100)
        
        success, result = place_service.get_places(
            group_id=group_id,
            user_id=g.user_id,
            page=page,
            per_page=per_page,
            q=request.args.get('q'),
            category=request.args.get('category'),
            visit_date_from=request.args.get('visit_date_from'),
            visit_date_to=request.args.get('visit_date_to'),
            sort_by=request.args.get('sort_by', 'created_at'),
            sort_order=request.args.get('sort_order', 'desc')
        )
        
        if success:
            return success_response(
                data=result.get('places', []),
                pagination=result.get('pagination')
            )
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Get places error: {str(e)}")
        return error_response('Failed to get places', 500)


@places_bp.route('/groups/<group_id>/places/<place_id>/vote', methods=['POST', 'OPTIONS'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
def vote_place(group_id, place_id):
    """
    Vote on a place (toggle vote)
    
    Request:
        POST /api/v2/group-planner/groups/<group_id>/places/<place_id>/vote
        Headers: Authorization: Bearer <token>
    """
    if request.method == 'OPTIONS':
        return success_response()
    
    try:
        from app.services.travel_place_service import place_service
        
        success, result = place_service.vote_place(
            group_id=group_id,
            place_id=place_id,
            user_id=g.user_id
        )
        
        if success:
            invalidate_cache('gp_places:*')
            return success_response(data=result)
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Vote place error: {str(e)}")
        return error_response('Failed to vote on place', 500)


@places_bp.route('/groups/<group_id>/places/<place_id>', methods=['PATCH', 'OPTIONS'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
@validate_schema(UpdatePlaceSchema)
def update_place(group_id, place_id):
    """
    Update place details
    
    Request:
        PATCH /api/v2/group-planner/groups/<group_id>/places/<place_id>
        Headers: Authorization: Bearer <token>
        Body: {
            "visit_date": "2025-06-05",
            "date": "2025-06-05",   (alias for visit_date)
            "suggested_duration": "2 hours",
            "duration": "2 hours",  (alias for suggested_duration)
            "remarks": "Must visit early",
            "notes": "Must visit early",  (alias for remarks)
            "time": "10:00 AM"  (visit time)
        }
    """
    if request.method == 'OPTIONS':
        return success_response()
    
    try:
        from app.services.travel_place_service import place_service
        
        data = g.validated_data
        
        # Support both backend and frontend field names
        # Use 'in' checks so empty strings (field clearing) are not swallowed by 'or'
        visit_date = data['visit_date'] if 'visit_date' in data else data.get('date')
        suggested_duration = data['suggested_duration'] if 'suggested_duration' in data else data.get('duration')
        remarks = data['remarks'] if 'remarks' in data else data.get('notes')
        suggested_time = data['suggested_time'] if 'suggested_time' in data else data.get('time')
        
        success, result = place_service.update_place(
            group_id=group_id,
            place_id=place_id,
            user_id=g.user_id,
            visit_date=visit_date,
            suggested_duration=suggested_duration,
            remarks=remarks,
            suggested_time=suggested_time,
            expected_updated_at=data.get('expected_updated_at')
        )
        
        if success:
            invalidate_cache('gp_places:*')
            return success_response(data=result.get('place'))
        else:
            status = result.get('status', 400)
            return error_response(result.get('error'), status)
            
    except Exception as e:
        logger.error(f"Update place error: {str(e)}")
        return error_response('Failed to update place', 500)


@places_bp.route('/groups/<group_id>/places/<place_id>/remarks', methods=['PUT', 'OPTIONS'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
@validate_schema(UpdatePlaceRemarksSchema)
def update_remarks(group_id, place_id):
    """
    Update place remarks
    
    Request:
        PUT /api/v2/group-planner/groups/<group_id>/places/<place_id>/remarks
        Headers: Authorization: Bearer <token>
        Body: {
            "remarks": "Great place to visit!"
        }
    """
    if request.method == 'OPTIONS':
        return success_response()
    
    try:
        from app.services.travel_place_service import place_service
        
        data = g.validated_data
        remarks = data.get('remarks', '')
        
        success, result = place_service.update_remarks(
            group_id=group_id,
            place_id=place_id,
            user_id=g.user_id,
            remarks=remarks
        )
        
        if success:
            invalidate_cache('gp_places:*')
            return success_response(data={
                'place_id': str(place_id),
                'remarks': remarks
            })
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Update remarks error: {str(e)}")
        return error_response('Failed to update remarks', 500)


@places_bp.route('/groups/<group_id>/places/<place_id>', methods=['DELETE', 'OPTIONS'])
@limit_api(Config.RATE_LIMITS['delete'])
@require_auth
@require_group_role('member')
def delete_place(group_id, place_id):
    """
    Delete a place
    
    Request:
        DELETE /api/v2/group-planner/groups/<group_id>/places/<place_id>
        Headers: Authorization: Bearer <token>
    """
    if request.method == 'OPTIONS':
        return success_response()
    
    try:
        from app.services.travel_place_service import place_service
        
        success, result = place_service.delete_place(
            group_id=group_id,
            place_id=place_id,
            user_id=g.user_id
        )
        
        if success:
            invalidate_cache('gp_places:*')
            invalidate_cache('gp_groups:*')
            return success_response(message=result.get('message'))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Delete place error: {str(e)}")
        return error_response('Failed to delete place', 500)


# =========================================================================
# GEOCODING PROXY
# =========================================================================

@places_bp.route('/geocode', methods=['POST', 'OPTIONS'])
@limit_api(Config.RATE_LIMITS['geocode'])
@require_auth
@validate_schema(GeocodeSchema)
def geocode_place():
    """
    Proxy geocoding requests to Nominatim
    
    Request:
        POST /api/v2/group-planner/geocode
        Body: {"place_name": "Tokyo Tower"}
    """
    if request.method == 'OPTIONS':
        return success_response()
    
    try:
        import pybreaker
        import requests
        from app.core.resilience import nominatim_breaker
        
        data = g.validated_data
        place_name = data['place_name'].strip()
        
        response = nominatim_breaker.call(
            requests.get,
            Config.NOMINATIM_BASE_URL,
            params={
                'format': 'json',
                'q': place_name,
                'limit': 1,
                'accept-language': 'en'
            },
            headers={
                'User-Agent': Config.NOMINATIM_USER_AGENT
            },
            timeout=Config.NOMINATIM_TIMEOUT
        )
        
        if response.status_code == 200:
            results = response.json()
            if results:
                result = results[0]
                return success_response(data={
                    'lat': float(result['lat']),
                    'lon': float(result['lon']),
                    'display_name': result['display_name']
                })
            else:
                return not_found_response('No results found')
        else:
            return error_response('Geocoding service error', 500)
            
    except pybreaker.CircuitBreakerError:
        logger.warning("Nominatim circuit breaker is open")
        return error_response('Geocoding service temporarily unavailable', 503)
    except Exception as e:
        logger.error(f"Geocode error: {str(e)}")
        return error_response('Geocoding failed', 500)
