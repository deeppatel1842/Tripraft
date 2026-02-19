"""
Poll Routes for Group Planner
Flask API routes for poll operations
"""

import logging
import traceback

from flask import Blueprint, g, jsonify, request
from app.infrastructure.auth.decorators import require_auth
from app.schemas.common import (CreatePollSchema, VotePollSchema,
                               validate_request)

logger = logging.getLogger(__name__)

# Create Blueprint
polls_bp = Blueprint(
    'gp_polls',  # Unique name for Group Planner
    __name__,
    url_prefix='/api/v2/group-planner'
)


# =========================================================================
# POLL ENDPOINTS
# =========================================================================

@polls_bp.route('/groups/<int:group_id>/polls', methods=['POST'])
@require_auth
def create_poll(group_id):
    """
    Create a poll in a group
    
    Request:
        POST /api/v2/group-planner/groups/<group_id>/polls
        Headers: Authorization: Bearer <token>
        Body: {
            "name": "When should we go?",  // or "question"
            "options": ["Spring", "Summer", "Fall"]
        }
    """
    try:
        from app.services.poll_service import poll_service
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body required'
            }), 400
        
        validated, errors = validate_request(CreatePollSchema, data)
        if errors:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'details': errors
            }), 400
        
        # Accept either 'name' or 'question' for the poll title
        poll_name = validated.get('name') or validated.get('question')
        
        if not poll_name:
            return jsonify({
                'success': False,
                'error': 'Poll name or question is required'
            }), 400
        
        success, result = poll_service.create_poll(
            group_id=group_id,
            user_id=g.user_id,
            name=poll_name,
            options=validated['options'],
            is_multiple_choice=validated.get('is_multiple_choice', False),
            expires_at=validated.get('expires_at')
        )
        
        if success:
            logger.info(f"Poll created in group {group_id}")
            return jsonify({'success': True, 'data': result.get('poll')}), 201
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Create poll error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create poll'
        }), 500


@polls_bp.route('/groups/<int:group_id>/polls', methods=['GET'])
@require_auth
def get_polls(group_id):
    """
    Get all polls for a group
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/polls
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.poll_service import poll_service
        
        success, result = poll_service.get_polls(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'data': result.get('polls', [])}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Get polls error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': True,
            'data': []
        }), 200


@polls_bp.route('/groups/<int:group_id>/polls/<int:poll_id>/vote', methods=['POST'])
@require_auth
def vote_poll(group_id, poll_id):
    """
    Vote on a poll
    
    Request:
        POST /api/v2/group-planner/groups/<group_id>/polls/<poll_id>/vote
        Headers: Authorization: Bearer <token>
        Body: {
            "option": "Summer"
        }
    """
    try:
        from app.services.poll_service import poll_service
        
        data = request.get_json() or {}
        validated, errors = validate_request(VotePollSchema, data)
        if errors:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'details': errors
            }), 400
        
        option = validated.get('option')
        option_index = validated.get('option_index')
        
        if option is None and option_index is None:
            return jsonify({
                'success': False,
                'error': 'Option or option_index is required'
            }), 400
        
        success, result = poll_service.vote_poll(
            group_id=group_id,
            poll_id=poll_id,
            user_id=g.user_id,
            option=option,
            option_index=option_index
        )
        
        if success:
            return jsonify({'success': True, 'data': result}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Vote poll error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to vote on poll'
        }), 500


@polls_bp.route('/groups/<int:group_id>/polls/<int:poll_id>', methods=['DELETE'])
@require_auth
def delete_poll(group_id, poll_id):
    """
    Delete a poll (creator only)
    
    Request:
        DELETE /api/v2/group-planner/groups/<group_id>/polls/<poll_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.poll_service import poll_service
        
        success, result = poll_service.delete_poll(
            group_id=group_id,
            poll_id=poll_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'message': result.get('message')}), 200
        else:
            status = 403 if 'creator' in result.get('error', '').lower() else 400
            return jsonify({'success': False, 'error': result.get('error')}), status
            
    except Exception as e:
        logger.error(f"Delete poll error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete poll'
        }), 500
