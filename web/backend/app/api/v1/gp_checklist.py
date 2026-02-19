"""
Checklist Routes for Group Planner
Flask API routes for checklist operations
"""

import logging

from app.infrastructure.auth.decorators import require_auth
from app.schemas.common import CreateChecklistItemSchema, validate_request
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

# Create Blueprint
checklist_bp = Blueprint(
    'gp_checklist',  # Unique name for Group Planner
    __name__,
    url_prefix='/api/v2/group-planner'
)


# =========================================================================
# CHECKLIST ENDPOINTS
# =========================================================================

@checklist_bp.route('/groups/<int:group_id>/checklist', methods=['POST'])
@require_auth
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
        from app.services.checklist_service import checklist_service
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body required'
            }), 400
        
        validated, errors = validate_request(CreateChecklistItemSchema, data)
        if errors:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'details': errors
            }), 400
        
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
            return jsonify({
                'success': True,
                'data': {'item': result.get('item')}
            }), 201
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Add checklist item error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to add checklist item'
        }), 500


@checklist_bp.route('/groups/<int:group_id>/checklist', methods=['GET'])
@require_auth
def get_group_checklist(group_id):
    """
    Get all checklist items for a group
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/checklist
        Headers: Authorization: Bearer <token>
        Query Params: ?category=travel&completed=false
    """
    try:
        from app.services.checklist_service import checklist_service
        
        category = request.args.get('category')
        completed = request.args.get('completed')
        
        # Convert completed string to bool
        if completed is not None:
            completed = completed.lower() == 'true'
        
        success, result = checklist_service.get_checklist(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({
                'success': True,
                'data': result.get('items', [])
            }), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Get checklist error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get checklist'
        }), 500


@checklist_bp.route('/checklist/<int:item_id>/toggle', methods=['POST', 'PATCH'])
@checklist_bp.route('/groups/<int:group_id>/checklist/<int:item_id>/toggle', methods=['POST', 'PATCH'])
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
        from app.domain.group_planner.models import ChecklistItem
        from app.infrastructure.db.connection import get_db_session
        from app.services.checklist_service import checklist_service

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
                    return jsonify({'success': False, 'error': 'Item not found'}), 404
        
        success, result = checklist_service.toggle_item(
            group_id=group_id,
            item_id=item_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({
                'success': True,
                'data': result.get('item')
            }), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 404
            
    except Exception as e:
        logger.error(f"Toggle checklist item error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to toggle checklist item'
        }), 500


@checklist_bp.route('/checklist/<int:item_id>', methods=['PUT', 'PATCH'])
@require_auth
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
        from app.services.checklist_service import checklist_service
        
        data = request.get_json()
        
        success, result = checklist_service.update_item(
            item_id=item_id,
            user_id=g.user_id,
            text=data.get('text'),
            category=data.get('category'),
            priority=data.get('priority'),
            due_date=data.get('due_date'),
            assigned_to_id=data.get('assigned_to_id'),
            completed=data.get('completed')
        )
        
        if success:
            return jsonify({
                'success': True,
                'data': result.get('item')
            }), 200
        else:
            status = 404 if 'not found' in result.get('error', '').lower() else 400
            return jsonify({'success': False, 'error': result.get('error')}), status
            
    except Exception as e:
        logger.error(f"Update checklist item error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update checklist item'
        }), 500


@checklist_bp.route('/checklist/<int:item_id>', methods=['DELETE'])
@checklist_bp.route('/groups/<int:group_id>/checklist/<int:item_id>', methods=['DELETE'])
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
        from app.services.checklist_service import checklist_service

        # If group_id not in URL, look it up from the item
        if group_id is None:
            from app.domain.group_planner.models import ChecklistItem
            from app.infrastructure.db.connection import get_db_session
            with get_db_session() as session:
                item = session.query(ChecklistItem).filter(
                    ChecklistItem.id == item_id,
                    ChecklistItem.is_deleted == False
                ).first()
                if item:
                    group_id = item.group_id
                else:
                    return jsonify({'success': False, 'error': 'Item not found'}), 404
        
        success, result = checklist_service.delete_item(
            group_id=group_id,
            item_id=item_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'message': result.get('message')}), 200
        else:
            status = 404 if 'not found' in result.get('error', '').lower() else 400
            return jsonify({'success': False, 'error': result.get('error')}), status
            
    except Exception as e:
        logger.error(f"Delete checklist item error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete checklist item'
        }), 500


@checklist_bp.route('/checklist/<int:item_id>/assign', methods=['POST'])
@require_auth
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
        from app.services.checklist_service import checklist_service
        
        data = request.get_json()
        assigned_to_id = data.get('assigned_to_id')
        
        success, result = checklist_service.update_item(
            item_id=item_id,
            user_id=g.user_id,
            assigned_to_id=assigned_to_id
        )
        
        if success:
            return jsonify({
                'success': True,
                'data': result.get('item')
            }), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Assign checklist item error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to assign checklist item'
        }), 500


@checklist_bp.route('/groups/<int:group_id>/checklist/stats', methods=['GET'])
@require_auth
def get_checklist_stats(group_id):
    """
    Get checklist statistics for a group
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/checklist/stats
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.checklist_service import checklist_service
        
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
            
            return jsonify({
                'success': True,
                'data': {
                    'total': total,
                    'completed': completed,
                    'pending': total - completed,
                    'completion_rate': round(completed / total * 100, 1) if total > 0 else 0,
                    'by_category': categories,
                    'pending_by_priority': priorities
                }
            }), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error(f"Get checklist stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get checklist stats'
        }), 500
