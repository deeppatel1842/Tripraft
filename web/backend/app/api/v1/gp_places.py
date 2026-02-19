"""
Place Routes for Group Planner
Flask API routes for place operations
"""

import logging

from flask import Blueprint, g, jsonify, request
from app.infrastructure.auth.decorators import require_auth
from app.schemas.common import AddPlaceSchema, validate_request

logger = logging.getLogger(__name__)

# Create Blueprint
places_bp = Blueprint(
    'gp_places',  # Unique name for Group Planner
    __name__,
    url_prefix='/api/v2/group-planner'
)


# =========================================================================
# PLACE ENDPOINTS
# =========================================================================

@places_bp.route('/groups/<int:group_id>/places', methods=['POST', 'OPTIONS'])
@require_auth
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
        return jsonify({'success': True}), 200
    
    try:
        from app.services.travel_place_service import place_service
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body required'
            }), 400
        
        validated, errors = validate_request(AddPlaceSchema, data)
        if errors:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'details': errors
            }), 400
        
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
            return jsonify({'success': True, 'data': result.get('place')}), 201
        else:
            status = 409 if result.get('code') == 'PLACE_ALREADY_EXISTS' else 400
            return jsonify({'success': False, 'error': result.get('error'), 'code': result.get('code')}), status
            
    except Exception as e:
        logger.error(f"Add place error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to add place'
        }), 500


@places_bp.route('/groups/<int:group_id>/places', methods=['GET'])
@require_auth
def get_places(group_id):
    """
    Get all places for a group
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/places
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_place_service import place_service
        
        success, result = place_service.get_places(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'data': result.get('places', [])}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Get places error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get places'
        }), 500


@places_bp.route('/groups/<int:group_id>/places/<int:place_id>/vote', methods=['POST', 'OPTIONS'])
@require_auth
def vote_place(group_id, place_id):
    """
    Vote on a place (toggle vote)
    
    Request:
        POST /api/v2/group-planner/groups/<group_id>/places/<place_id>/vote
        Headers: Authorization: Bearer <token>
    """
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        from app.services.travel_place_service import place_service
        
        success, result = place_service.vote_place(
            group_id=group_id,
            place_id=place_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'data': result}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Vote place error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to vote on place'
        }), 500


@places_bp.route('/groups/<int:group_id>/places/<int:place_id>', methods=['PATCH', 'OPTIONS'])
@require_auth
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
        return jsonify({'success': True}), 200
    
    try:
        from app.services.travel_place_service import place_service
        
        data = request.get_json()
        
        # Support both backend and frontend field names
        visit_date = data.get('visit_date') or data.get('date')
        suggested_duration = data.get('suggested_duration') or data.get('duration')
        remarks = data.get('remarks') or data.get('notes')
        visit_time = data.get('time')  # Optional time field
        
        # Combine date and time if both provided
        if visit_date and visit_time:
            remarks_prefix = f"Time: {visit_time}"
            if remarks:
                remarks = f"{remarks_prefix}\n{remarks}"
            else:
                remarks = remarks_prefix
        
        success, result = place_service.update_place(
            group_id=group_id,
            place_id=place_id,
            user_id=g.user_id,
            visit_date=visit_date,
            suggested_duration=suggested_duration,
            remarks=remarks
        )
        
        if success:
            return jsonify({'success': True, 'data': result.get('place')}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Update place error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update place'
        }), 500


@places_bp.route('/groups/<int:group_id>/places/<int:place_id>/remarks', methods=['PUT', 'OPTIONS'])
@require_auth
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
        return jsonify({'success': True}), 200
    
    try:
        from app.services.travel_place_service import place_service
        
        data = request.get_json()
        remarks = data.get('remarks', '')
        
        success, result = place_service.update_remarks(
            group_id=group_id,
            place_id=place_id,
            user_id=g.user_id,
            remarks=remarks
        )
        
        if success:
            return jsonify({
                'success': True,
                'data': {
                    'place_id': str(place_id),
                    'remarks': remarks
                }
            }), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Update remarks error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update remarks'
        }), 500


@places_bp.route('/groups/<int:group_id>/places/<int:place_id>', methods=['DELETE', 'OPTIONS'])
@require_auth
def delete_place(group_id, place_id):
    """
    Delete a place
    
    Request:
        DELETE /api/v2/group-planner/groups/<group_id>/places/<place_id>
        Headers: Authorization: Bearer <token>
    """
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        from app.services.travel_place_service import place_service
        
        success, result = place_service.delete_place(
            group_id=group_id,
            place_id=place_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'message': result.get('message')}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Delete place error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete place'
        }), 500


# =========================================================================
# GEOCODING PROXY
# =========================================================================

@places_bp.route('/geocode', methods=['POST', 'OPTIONS'])
def geocode_place():
    """
    Proxy geocoding requests to Nominatim
    
    Request:
        POST /api/v2/group-planner/geocode
        Body: {"place_name": "Tokyo Tower"}
    """
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        import requests
        
        data = request.get_json()
        place_name = data.get('place_name', '').strip()
        
        if not place_name:
            return jsonify({
                'success': False,
                'error': 'Place name is required'
            }), 400
        
        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={
                'format': 'json',
                'q': place_name,
                'limit': 1,
                'accept-language': 'en'
            },
            headers={
                'User-Agent': 'TripRaft/1.0 (contact@tripraft.com)'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            results = response.json()
            if results:
                result = results[0]
                return jsonify({
                    'success': True,
                    'data': {
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result['display_name']
                    }
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'No results found'
                }), 404
        else:
            return jsonify({
                'success': False,
                'error': f'Geocoding service error'
            }), 500
            
    except Exception as e:
        logger.error(f"Geocode error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Geocoding failed'
        }), 500
