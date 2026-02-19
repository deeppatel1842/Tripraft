"""Group Routes for Group Planner
Flask API routes for group operations

Uses unified database - same users as expense_engine
"""

import logging

from app.infrastructure.auth.decorators import require_auth
from app.schemas.common import (CreateTravelGroupSchema, UpdateBudgetSchema,
                                validate_request)
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

# Create Blueprint
groups_bp = Blueprint(
    'gp_groups',  # Unique name to avoid conflict with expense_engine
    __name__,
    url_prefix='/api/v2/group-planner'
)


# =========================================================================
# GROUP ENDPOINTS
# =========================================================================

@groups_bp.route('/groups', methods=['POST'])
@require_auth
def create_group():
    """
    Create a new travel group
    
    Request:
        POST /api/v2/group-planner/groups
        Headers: Authorization: Bearer <token>
        Body: {
            "name": "Bali Trip",
            "description": "Summer vacation",
            "destination": "Bali, Indonesia",
            "start_date": "2025-06-01",
            "end_date": "2025-06-15",
            "estimated_budget": 5000
        }
    """
    try:
        from app.services.travel_group_service import group_service
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body required'
            }), 400
        
        validated, errors = validate_request(CreateTravelGroupSchema, data)
        if errors:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'details': errors
            }), 400
        
        success, result = group_service.create_group(
            user_id=g.user_id,
            name=validated['name'],
            description=validated.get('description'),
            destination=validated.get('destination'),
            destination_lat=validated.get('destination_lat'),
            destination_lng=validated.get('destination_lng'),
            destination_type=validated.get('destination_type'),
            destination_id=validated.get('destination_id'),
            start_date=validated.get('start_date'),
            end_date=validated.get('end_date'),
            estimated_budget=validated.get('estimated_budget'),
            budget_currency=validated.get('budget_currency', 'USD')
        )
        
        if success:
            logger.info("Group created by user %s", g.user_id)
            group_data = result.get('group') if isinstance(result, dict) else None
            return jsonify({'success': True, 'data': group_data}), 201
        else:
            error_msg = result.get('error') if isinstance(result, dict) else str(result)
            return jsonify({'success': False, 'error': error_msg}), 400
            
    except Exception as e:
        logger.error("Create group error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to create group'
        }), 500


@groups_bp.route('/user/groups', methods=['GET'])
@require_auth
def get_user_groups():
    """
    Get all groups for current user
    
    Request:
        GET /api/v2/group-planner/user/groups
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_group_service import group_service
        
        success, result = group_service.get_user_groups(user_id=g.user_id)
        
        if success:
            return jsonify({'success': True, 'data': result.get('groups', [])}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error("Get user groups error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to get groups'
        }), 500


@groups_bp.route('/groups/<int:group_id>', methods=['GET'])
@require_auth
def get_group(group_id):
    """
    Get a specific group with all details
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_group_service import group_service
        
        success, result = group_service.get_group(
            group_id=group_id,
            user_id=g.user_id,
            include_all=True
        )
        
        if success:
            return jsonify({'success': True, 'data': result.get('group')}), 200
        else:
            status = 403 if 'member' in result.get('error', '').lower() else 404
            return jsonify({'success': False, 'error': result.get('error')}), status
            
    except Exception as e:
        logger.error("Get group error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to get group'
        }), 500


@groups_bp.route('/groups/<int:group_id>', methods=['PUT'])
@require_auth
def update_group(group_id):
    """
    Update group details
    
    Request:
        PUT /api/v2/group-planner/groups/<group_id>
        Headers: Authorization: Bearer <token>
        Body: {
            "name": "Updated Name",
            "description": "Updated description"
        }
    """
    try:
        from app.services.travel_group_service import group_service
        
        data = request.get_json() or {}
        
        # Only pass supported fields to avoid unexpected keyword arguments
        allowed_fields = {
            'name', 'description', 'destination', 'start_date', 'end_date',
            'estimated_budget', 'budget_currency'
        }
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        success, result = group_service.update_group(
            group_id=group_id,
            user_id=g.user_id,
            **filtered_data
        )
        
        if success:
            return jsonify({'success': True, 'data': result.get('group')}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error("Update group error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to update group'
        }), 500


@groups_bp.route('/groups/<int:group_id>', methods=['DELETE'])
@require_auth
def delete_group(group_id):
    """
    Delete a group (creator only)
    
    Request:
        DELETE /api/v2/group-planner/groups/<group_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_group_service import group_service
        
        success, result = group_service.delete_group(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'message': result.get('message')}), 200
        else:
            status = 403 if 'creator' in result.get('error', '').lower() else 404
            return jsonify({'success': False, 'error': result.get('error')}), status
            
    except Exception as e:
        logger.error("Delete group error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to delete group'
        }), 500


@groups_bp.route('/groups/<int:group_id>/itinerary-document', methods=['PUT'])
@groups_bp.route('/groups/<int:group_id>/itinerary', methods=['PUT'])
@require_auth
def update_itinerary_document(group_id):
    """
    Update itinerary document content
    
    Request:
        PUT /api/v2/group-planner/groups/<group_id>/itinerary-document
        Headers: Authorization: Bearer <token>
        Body: {
            "content": "# Day 1\n- Morning: Arrive..."
        }
    """
    try:
        from app.services.travel_group_service import group_service
        
        data = request.get_json() or {}
        content = data.get('content', data.get('itinerary_document', ''))
        
        success, result = group_service.update_itinerary_document(
            group_id=group_id,
            user_id=g.user_id,
            content=content
        )
        
        if success:
            return jsonify({'success': True, 'data': result}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error("Update itinerary document error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to update itinerary document'
        }), 500


@groups_bp.route('/groups/<int:group_id>/members/<int:member_id>', methods=['DELETE'])
@require_auth
def remove_member(group_id, member_id):
    """
    Remove a member from group (creator only)
    
    Request:
        DELETE /api/v2/group-planner/groups/<group_id>/members/<member_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_group_service import group_service
        
        success, result = group_service.remove_member(
            group_id=group_id,
            member_id=member_id,
            requester_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'message': result.get('message')}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error("Remove member error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to remove member'
        }), 500





@groups_bp.route('/groups/<int:group_id>/budget', methods=['PUT', 'PATCH'])
@require_auth
def update_budget(group_id):
    """
    Update group budget
    
    Request:
        PATCH /api/v2/group-planner/groups/<group_id>/budget
        Headers: Authorization: Bearer <token>
        Body: {
            "estimated_budget": 5000
        }
    """
    try:
        from app.services.travel_group_service import group_service
        
        data = request.get_json()
        
        validated, errors = validate_request(UpdateBudgetSchema, data)
        if errors:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'details': errors
            }), 400
        
        success, result = group_service.update_budget(
            group_id=group_id,
            user_id=g.user_id,
            estimated_budget=validated['estimated_budget'],
            budget_currency=validated.get('budget_currency')
        )
        
        if success:
            return jsonify({'success': True, 'data': result}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error("Update budget error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to update budget'
        }), 500


@groups_bp.route('/groups/<int:group_id>/expense-summary', methods=['GET'])
@require_auth
def get_expense_summary(group_id):
    """
    Get expense summary for a linked expense group
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/expense-summary
        Headers: Authorization: Bearer <token>
        
    Response:
        {
            "linked": true,
            "expense_group_id": 123,
            "total_spent": 450.00,
            "per_person": 112.50,
            "estimated_budget": 1200.00,
            "member_count": 4,
            "expense_count": 8
        }
    """
    try:
        from app.services.travel_group_service import group_service
        
        success, result = group_service.get_expense_summary(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'data': result}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error("Get expense summary error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to get expense summary'
        }), 500


@groups_bp.route('/groups/<int:group_id>/link-expense', methods=['POST'])
@require_auth
def link_expense_group(group_id):
    """
    Link travel group to expense engine group
    Creates a new expense group with same members
    
    Request:
        POST /api/v2/group-planner/groups/<group_id>/link-expense
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.expense_group_service import \
            GroupServiceSQL as expense_group_service_cls
        expense_group_service = expense_group_service_cls()

        from app.services.travel_group_service import group_service

        # First get the travel group to get its details
        success, result = group_service.get_group(
            group_id=group_id,
            user_id=g.user_id,
            include_all=True
        )
        
        if not success:
            return jsonify({'success': False, 'error': result.get('error')}), 400
        
        group_data = result.get('group', {})
        
        # Check if already linked
        if group_data.get('expense_group_id'):
            return jsonify({
                'success': True,
                'data': {'expense_group_id': group_data['expense_group_id']},
                'message': 'Already linked'
            }), 200
        
        # Create expense group
        expense_success, expense_result = expense_group_service.create_group(
            user_id=g.user_id,
            name=group_data.get('name'),
            description=f"Linked from Group Planner - {group_data.get('destination', 'Trip')}",
            currency='USD'
        )
        
        if not expense_success:
            logger.error("Failed to create expense group: %s", expense_result)
            return jsonify({'success': False, 'error': 'Failed to create expense group'}), 500
        
        expense_group_id = expense_result.get('group', {}).get('id')
        logger.info("Created expense group %s for travel group %s", expense_group_id, group_id)
        
        # Add existing members to expense group
        members = group_data.get('member_details', [])
        added_count = 0
        for member in members:
            member_user_id = member.get('user_id')
            member_email = member.get('email')
            
            # Skip the creator (they're already added as admin)
            if member_user_id and member_user_id != g.user_id and member_email:
                try:
                    add_success, add_result = expense_group_service.add_member(
                        group_id=expense_group_id,
                        user_id=g.user_id,
                        member_email=member_email,
                        role='member'
                    )
                    if add_success:
                        added_count += 1
                        logger.info("Added member %s to expense group", member_email)
                    else:
                        logger.warning("Could not add member %s: %s", member_email, add_result.get('error'))
                except Exception as e:
                    logger.warning("Error adding member %s: %s", member_email, e)
        
        logger.info("Added %s members to expense group %s", added_count, expense_group_id)
        
        # Link the groups
        link_success, link_result = group_service.link_expense_group(
            group_id=group_id,
            user_id=g.user_id,
            expense_group_id=expense_group_id
        )
        
        if link_success:
            return jsonify({
                'success': True,
                'data': {
                    'expense_group_id': expense_group_id,
                    'members_added': added_count
                }
            }), 200
        else:
            return jsonify({'success': False, 'error': link_result.get('error')}), 400
            
    except Exception as e:
        logger.error("Link expense group error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to link expense group'
        }), 500


@groups_bp.route('/groups/<int:group_id>/unlink-expense', methods=['POST'])
@require_auth
def unlink_expense_group(group_id):
    """
    Unlink travel group from expense engine group
    
    Request:
        POST /api/v2/group-planner/groups/<group_id>/unlink-expense
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_group_service import group_service
        
        success, result = group_service.unlink_expense_group(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if success:
            return jsonify({'success': True, 'message': result.get('message')}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error("Unlink expense group error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to unlink expense group'
        }), 500


@groups_bp.route('/groups/<int:group_id>/activities', methods=['GET'])
@require_auth
def get_group_activities(group_id):
    """
    Get recent group activities (for real-time updates)
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/activities
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_group_service import group_service
        
        limit = request.args.get('limit', 50, type=int)
        
        success, result = group_service.get_group_activities(
            group_id=group_id,
            user_id=g.user_id,
            limit=limit
        )
        
        if success:
            return jsonify({'success': True, 'data': result.get('activities', [])}), 200
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400
            
    except Exception as e:
        logger.error("Get activities error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to get activities'
        }), 500


# =========================================================================
# MEMBER MANAGEMENT  
# =========================================================================

@groups_bp.route('/groups/<int:group_id>/members', methods=['GET'])
@require_auth
def get_group_members(group_id: int):
    """
    Get detailed member list with owner indicator
    
    Request:
        GET /api/v2/group-planner/groups/{group_id}/members
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_group_service import group_service
        
        success, result = group_service.get_group_members_detailed(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to get members')
            }), 400
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error("Get group members error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to get group members'
        }), 500


@groups_bp.route('/groups/<int:group_id>/leave', methods=['POST'])
@require_auth
def leave_group(group_id: int):
    """
    Leave a group (non-owner members only)

    Request:
        POST /api/v2/group-planner/groups/<group_id>/leave
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.services.travel_group_service import group_service

        success, result = group_service.leave_group(
            group_id=group_id,
            user_id=g.user_id,
        )

        if not success:
            status = 403 if 'owner' in result.get('error', '').lower() else 400
            return jsonify({'success': False, 'error': result.get('error')}), status

        return jsonify({'success': True, 'message': result.get('message')}), 200

    except Exception as e:
        logger.error("Leave group error: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to leave group'
        }), 500


# =========================================================================
# AUTH VERIFICATION
# =========================================================================

@groups_bp.route('/auth/verify', methods=['POST'])
@require_auth
def verify_auth():
    """
    Verify authentication token
    
    Request:
        POST /api/v2/group-planner/auth/verify
        Headers: Authorization: Bearer <token>
    """
    return jsonify({
        'success': True,
        'message': 'Authentication verified',
        'data': {
            'user': {
                'uid': g.user_id,
                'email': g.user_email
            },
            'token': {
                'status': 'valid',
                'present': True
            }
        }
    }), 200


@groups_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint (no auth required)
    """
    return jsonify({
        'success': True,
        'service': 'Group Planner API (SQL)',
        'version': '2.0.0',
        'status': 'healthy'
    }), 200
