# Purpose: Checklist Routes for Group Planner Flask API routes for checklist operations.
"""
Checklist Routes for Group Planner
Flask API routes for checklist operations
"""

import logging

from app.core.apiutils.responses import (created_response, error_response,
                                     not_found_response, success_response,
                                     validation_error_response)
from app.core.apiutils.validators import parse_query_int, validate_schema
from app.core.config import Config
from app.core.exceptions import ValidationError as RequestValidationError
from app.core.rate_limiter import limit_api
from app.auth.security.decorators import require_auth, require_group_role
from app.core.cache.redis import cache_response, invalidate_cache
from app.core.schemas.common import CreateChecklistItemSchema, validate_request
from app.core.schemas.gp_checklist import (AssignChecklistItemSchema,
                                      UpdateChecklistItemSchema)
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

# Create Blueprint
checklist_bp = Blueprint(
    'gp_checklist',  # Unique name for Group Planner
    __name__,
    url_prefix='/api/v1/group-planner'
)


# =========================================================================
# CHECKLIST ENDPOINTS
# =========================================================================

@checklist_bp.route('/groups/<group_id>/checklist', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
@require_group_role('member')
def add_checklist_item(group_id):
    """
    Add a checklist item to a group
    
    Request:
        POST /api/v2/group-planner/groups/<group_id>/checklist
        Headers: Authorization: Bearer <token>
        Body: {
            "text": "Book flight tickets",
            "category": "travel",
            "priority": "high",
            "due_date": "2024-03-15",
            "assigned_to_id": 2
        }
    """
    try:
        from app.itinerary.services.checklist_service import checklist_service
        
        data = request.get_json(silent=True)
        
        if not data:
            return error_response('Request body required')
        
        validated, errors = validate_request(CreateChecklistItemSchema, data)
        if errors:
            return validation_error_response(errors)
        
        success, result = checklist_service.add_item(
            group_id=group_id,
            text=validated['text'],
            created_by_id=g.user_id,
            category=validated.get('category'),
            priority=validated.get('priority', 'medium'),
            due_date=validated.get('due_date'),
            assigned_to_id=validated.get('assigned_to_id')
        )
        
        if success:
            invalidate_cache('gp_checklist:*')
            return created_response(data=result.get('item'))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Add checklist item error: {str(e)}")
        return error_response('Failed to add checklist item', 500)


@checklist_bp.route('/groups/<group_id>/checklist', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_checklist:list', ttl=Config.CACHE_TTLS['group_list'], vary_on_user=True)
def get_group_checklist(group_id):
    """
    Get checklist items for a group (paginated)
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/checklist?page=1&per_page=50
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.itinerary.services.checklist_service import checklist_service
        
        page = parse_query_int('page', 1, minimum=1)
        per_page = parse_query_int('per_page', 50, minimum=1, maximum=100)
        completed_param = request.args.get('completed')
        completed = None
        if completed_param is not None:
            completed = completed_param.lower() in ('true', '1', 'yes')
        
        success, result = checklist_service.get_checklist(
            group_id=group_id,
            user_id=g.user_id,
            page=page,
            per_page=per_page,
            completed=completed,
            q=request.args.get('q'),
            sort_by=request.args.get('sort_by', 'created_at'),
            sort_order=request.args.get('sort_order', 'asc')
        )
        
        if success:
            return success_response(
                data=result.get('checklist', []),
                pagination=result.get('pagination')
            )
        else:
            return error_response(result.get('error'))
            
    except RequestValidationError:
        raise
    except Exception as e:
        logger.error(f"Get checklist error: {str(e)}")
        return error_response('Failed to get checklist', 500)


@checklist_bp.route('/checklist/<item_id>/toggle', methods=['POST', 'PATCH'])
@checklist_bp.route('/groups/<group_id>/checklist/<item_id>/toggle', methods=['POST', 'PATCH'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
def toggle_checklist_item(item_id, group_id=None):
    """
    Toggle a checklist item completion status
    
    Request:
        POST /api/v2/group-planner/checklist/<item_id>/toggle
        Headers: Authorization: Bearer <token>
        Body: { "group_id": 1 }  (optional - will look up if not provided)
    """
    try:
        from app.trips.models import ChecklistItem, TripMember
        from app.core.db.connection import get_db_session
        from app.itinerary.services.checklist_service import checklist_service

        # Try to get group_id from URL param, request body, then look it up
        data = request.get_json(silent=True) or {}
        if not group_id:
            group_id = data.get('group_id')
        
        if not group_id:
            # Look up group_id from the checklist item
            with get_db_session() as session:
                item = session.query(ChecklistItem).filter(
                    ChecklistItem.id == item_id
                ).first()
                if item:
                    group_id = item.group_id
                else:
                    return not_found_response('Item not found')

        # Validate membership
        with get_db_session() as session:
            member = session.query(TripMember).filter(
                TripMember.group_id == group_id,
                TripMember.user_id == g.user_id,
                TripMember.is_active == True,
            ).first()
            if not member:
                return error_response('Not a member of this group', 403)
        
        success, result = checklist_service.toggle_item(
            group_id=group_id,
            item_id=item_id,
            user_id=g.user_id
        )
        
        if success:
            invalidate_cache('gp_checklist:*')
            return success_response(data=result.get('item'))
        else:
            return error_response(result.get('error'), 404)
            
    except Exception as e:
        logger.error(f"Toggle checklist item error: {str(e)}")
        return error_response('Failed to toggle checklist item', 500)


@checklist_bp.route('/checklist/<item_id>', methods=['PUT', 'PATCH'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
@validate_schema(UpdateChecklistItemSchema)
def update_checklist_item(item_id):
    """
    Update a checklist item
    
    Request:
        PUT /api/v2/group-planner/checklist/<item_id>
        Headers: Authorization: Bearer <token>
        Body: {
            "text": "Updated task",
            "category": "accommodation",
            "priority": "low",
            "due_date": "2024-03-20",
            "assigned_to_id": 3,
            "completed": true
        }
    """
    try:
        from app.itinerary.services.checklist_service import checklist_service
        
        data = g.validated_data
        
        updates = {
            field: data[field]
            for field in ('text', 'category', 'priority', 'due_date', 'assigned_to_id', 'completed')
            if field in data
        }
        success, result = checklist_service.update_item(
            item_id=item_id,
            user_id=g.user_id,
            **updates,
        )
        
        if success:
            invalidate_cache('gp_checklist:*')
            return success_response(data=result.get('item'))
        else:
            status = 404 if 'not found' in result.get('error', '').lower() else 400
            return error_response(result.get('error'), status)
            
    except Exception as e:
        logger.error(f"Update checklist item error: {str(e)}")
        return error_response('Failed to update checklist item', 500)


@checklist_bp.route('/checklist/<item_id>', methods=['DELETE'])
@checklist_bp.route('/groups/<group_id>/checklist/<item_id>', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
@require_auth
def delete_checklist_item(item_id, group_id=None):
    """
    Delete a checklist item
    
    Request:
        DELETE /api/v2/group-planner/checklist/<item_id>
        DELETE /api/v2/group-planner/groups/<group_id>/checklist/<item_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.itinerary.services.checklist_service import checklist_service

        # If group_id not in URL, look it up from the item
        if group_id is None:
            from app.trips.models import ChecklistItem
            from app.core.db.connection import get_db_session
            with get_db_session() as session:
                item = session.query(ChecklistItem).filter(
                    ChecklistItem.id == item_id,
                    ChecklistItem.is_deleted == False
                ).first()
                if item:
                    group_id = item.group_id
                else:
                    return not_found_response('Item not found')

        # Validate membership
        from app.trips.models import TripMember
        from app.core.db.connection import get_db_session
        with get_db_session() as session:
            member = session.query(TripMember).filter(
                TripMember.group_id == group_id,
                TripMember.user_id == g.user_id,
                TripMember.is_active == True,
            ).first()
            if not member:
                return error_response('Not a member of this group', 403)
        
        success, result = checklist_service.delete_item(
            group_id=group_id,
            item_id=item_id,
            user_id=g.user_id
        )
        
        if success:
            invalidate_cache('gp_checklist:*')
            return success_response(message=result.get('message'))
        else:
            status = 404 if 'not found' in result.get('error', '').lower() else 400
            return error_response(result.get('error'), status)
            
    except Exception as e:
        logger.error(f"Delete checklist item error: {str(e)}")
        return error_response('Failed to delete checklist item', 500)


@checklist_bp.route('/checklist/<item_id>/assign', methods=['POST'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
@validate_schema(AssignChecklistItemSchema)
def assign_checklist_item(item_id):
    """
    Assign a checklist item to a group member
    
    Request:
        POST /api/v2/group-planner/checklist/<item_id>/assign
        Headers: Authorization: Bearer <token>
        Body: {
            "assigned_to_id": 2
        }
    """
    try:
        from app.itinerary.services.checklist_service import checklist_service
        
        data = g.validated_data
        assigned_to_id = data['assigned_to_id']
        
        success, result = checklist_service.update_item(
            item_id=item_id,
            user_id=g.user_id,
            assigned_to_id=assigned_to_id
        )
        
        if success:
            invalidate_cache('gp_checklist:*')
            return success_response(data=result.get('item'))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Assign checklist item error: {str(e)}")
        return error_response('Failed to assign checklist item', 500)


@checklist_bp.route('/groups/<group_id>/checklist/stats', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_checklist:stats', ttl=Config.CACHE_TTLS['stats'], vary_on_user=True)
def get_checklist_stats(group_id):
    """
    Get checklist statistics for a group
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/checklist/stats
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.itinerary.services.checklist_service import checklist_service
        
        success, result = checklist_service.get_checklist(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if success:
            items = result.get('checklist', [])
            total = len(items)
            completed = sum(1 for item in items if item.get('completed'))
            
            # Category breakdown
            categories = {}
            for item in items:
                cat = item.get('category') or 'uncategorized'
                if cat not in categories:
                    categories[cat] = {'total': 0, 'completed': 0}
                categories[cat]['total'] += 1
                if item.get('completed'):
                    categories[cat]['completed'] += 1
            
            # Priority breakdown
            priorities = {'high': 0, 'medium': 0, 'low': 0}
            for item in items:
                if not item.get('completed'):
                    priority = item.get('priority') or 'medium'
                    priorities[priority] = priorities.get(priority, 0) + 1
            
            return success_response(data={
                'total': total,
                'completed': completed,
                'pending': total - completed,
                'completion_rate': round(completed / total * 100, 1) if total > 0 else 0,
                'by_category': categories,
                'pending_by_priority': priorities
            })
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error(f"Get checklist stats error: {str(e)}")
        return error_response('Failed to get checklist stats', 500)
