# Purpose: Poll Routes for Group Planner Flask API routes for poll operations.
"""
Poll Routes for Group Planner
Flask API routes for poll operations
"""

import logging
import traceback

from app.core.apiutils.responses import (created_response, error_response,
                                     success_response,
                                     validation_error_response)
from app.core.apiutils.validators import parse_query_int
from app.core.config import Config
from app.core.exceptions import ValidationError as RequestValidationError
from app.core.rate_limiter import limit_api
from app.auth.security.decorators import require_auth, require_group_role
from app.core.cache.redis import cache_response, invalidate_cache
from app.core.schemas.common import (CreatePollSchema, VotePollSchema,
                                validate_request)
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

# Create Blueprint
polls_bp = Blueprint(
    'gp_polls',  # Unique name for Group Planner
    __name__,
    url_prefix='/api/v1/group-planner'
)


# =========================================================================
# POLL ENDPOINTS
# =========================================================================

@polls_bp.route('/groups/<group_id>/polls', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
@require_group_role('member')
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
        from app.trips.services.poll_service import poll_service
        
        data = request.get_json(silent=True)
        
        if not data:
            return error_response('Request body required')
        
        validated, errors = validate_request(CreatePollSchema, data)
        if errors:
            return validation_error_response(errors)
        
        # Accept either 'name' or 'question' for the poll title
        poll_name = validated.get('name') or validated.get('question')
        
        if not poll_name:
            return error_response('Poll name or question is required')
        
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
            invalidate_cache('gp_polls:*')
            invalidate_cache('gp_groups:*')
            return created_response(data=result.get('poll'))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Create poll error: {str(e)}")
        return error_response('Failed to create poll', 500)


@polls_bp.route('/groups/<group_id>/polls', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_polls:list', ttl=Config.CACHE_TTLS['group_list'], vary_on_user=True)
def get_polls(group_id):
    """
    Get polls for a group (paginated)
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/polls?page=1&per_page=20
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.trips.services.poll_service import poll_service
        
        page = parse_query_int('page', 1, minimum=1)
        per_page = parse_query_int(
            'per_page', Config.GP_DEFAULT_LIMIT, minimum=1, maximum=100,
        )
        active_param = request.args.get('active')
        active = None
        if active_param is not None:
            active = active_param.lower() in ('true', '1', 'yes')
        
        success, result = poll_service.get_polls(
            group_id=group_id,
            user_id=g.user_id,
            page=page,
            per_page=per_page,
            active=active
        )
        
        if success:
            return success_response(
                data=result.get('polls', []),
                pagination=result.get('pagination')
            )
        else:
            return error_response(result.get('error'))
            
    except RequestValidationError:
        raise
    except Exception as e:
        logger.error(f"Get polls error: {str(e)}\n{traceback.format_exc()}")
        return success_response(data=[])


@polls_bp.route('/groups/<group_id>/polls/<poll_id>/vote', methods=['POST'])
@limit_api(Config.RATE_LIMITS['update'])
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
        from app.trips.services.poll_service import poll_service
        
        data = request.get_json(silent=True) or {}
        validated, errors = validate_request(VotePollSchema, data)
        if errors:
            return validation_error_response(errors)
        
        option = validated.get('option')
        option_index = validated.get('option_index')
        
        if option is None and option_index is None:
            return error_response('Option or option_index is required')
        
        success, result = poll_service.vote_poll(
            group_id=group_id,
            poll_id=poll_id,
            user_id=g.user_id,
            option=option,
            option_index=option_index
        )
        
        if success:
            invalidate_cache('gp_polls:*')
            return success_response(data=result)
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Vote poll error: {str(e)}")
        return error_response('Failed to vote on poll', 500)


@polls_bp.route('/groups/<group_id>/polls/<poll_id>', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
@require_auth
@require_group_role('admin')
def delete_poll(group_id, poll_id):
    """
    Delete a poll (creator only)
    
    Request:
        DELETE /api/v2/group-planner/groups/<group_id>/polls/<poll_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.trips.services.poll_service import poll_service
        
        success, result = poll_service.delete_poll(
            group_id=group_id,
            poll_id=poll_id,
            user_id=g.user_id
        )
        
        if success:
            invalidate_cache('gp_polls:*')
            invalidate_cache('gp_groups:*')
            return success_response(message=result.get('message'))
        else:
            status = 403 if 'creator' in result.get('error', '').lower() else 400
            return error_response(result.get('error'), status)
            
    except Exception as e:
        logger.error(f"Delete poll error: {str(e)}")
        return error_response('Failed to delete poll', 500)
