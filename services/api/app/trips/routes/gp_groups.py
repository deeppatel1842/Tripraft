# Purpose: Group Routes for Group Planner Flask API routes for group operations.
"""Group Routes for Group Planner
Flask API routes for group operations

Uses unified database - same users as expense_engine
"""

import logging

from app.core.apiutils.responses import (created_response, error_response,
                                     success_response,
                                     validation_error_response)
from app.core.apiutils.validators import parse_query_int, validate_schema
from app.core.config import Config
from app.core.exceptions import ValidationError as RequestValidationError
from app.core.rate_limiter import limit_api
from app.auth.security.decorators import require_auth, require_group_role
from app.core.cache.redis import cache_response, invalidate_cache
from app.core.schemas.common import (CreateTravelGroupSchema, UpdateBudgetSchema,
                                validate_request)
from app.core.schemas.group_planner import (UpdateItineraryDocumentSchema,
                                       UpdateTravelGroupSchema)
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

# Create Blueprint
groups_bp = Blueprint(
    'gp_groups',  # Unique name to avoid conflict with expense_engine
    __name__,
    url_prefix='/api/v1/group-planner'
)


# =========================================================================
# GROUP ENDPOINTS
# =========================================================================

def _invalidate_gp_caches():
    """Invalidate all group-planner caches."""
    invalidate_cache('gp_groups:*')
    invalidate_cache('gp_places:*')
    invalidate_cache('gp_polls:*')
    invalidate_cache('gp_checklist:*')
    invalidate_cache('gp_invitations:*')


@groups_bp.route('/groups', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
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
        from app.trips.services.travel_group_service import group_service
        
        data = request.get_json(silent=True)
        
        if not data:
            return error_response('Request body required')
        
        validated, errors = validate_request(CreateTravelGroupSchema, data)
        if errors:
            return validation_error_response(errors)
        
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
            _invalidate_gp_caches()
            group_data = result.get('group') if isinstance(result, dict) else None
            return created_response(data=group_data)
        else:
            error_msg = result.get('error') if isinstance(result, dict) else str(result)
            return error_response(error_msg)
            
    except Exception as e:
        logger.error("Create group error: %s", e)
        return error_response('Failed to create group', 500)


@groups_bp.route('/user/groups', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_groups:user_list', ttl=Config.CACHE_TTLS['group_list'], vary_on_user=True)
def get_user_groups():
    """
    Get all groups for current user (paginated)
    
    Request:
        GET /api/v2/group-planner/user/groups?page=1&per_page=20
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.trips.services.travel_group_service import group_service
        
        page = parse_query_int('page', 1, minimum=1)
        per_page = parse_query_int(
            'per_page', Config.GP_DEFAULT_LIMIT, minimum=1, maximum=100,
        )
        
        success, result = group_service.get_user_groups(
            user_id=g.user_id,
            page=page,
            per_page=per_page
        )
        
        if success:
            return success_response(
                data=result.get('groups', []),
                pagination=result.get('pagination')
            )
        else:
            return error_response(result.get('error'))
            
    except RequestValidationError:
        raise
    except Exception as e:
        logger.error("Get user groups error: %s", e)
        return error_response('Failed to get groups', 500)


@groups_bp.route('/groups/<group_id>', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_heavy'])
@require_auth
@cache_response(key_prefix='gp_groups:detail', ttl=Config.CACHE_TTLS['group_detail'], vary_on_user=True)
def get_group(group_id):
    """
    Get a specific group with all details
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.trips.services.travel_group_service import group_service
        
        success, result = group_service.get_group(
            group_id=group_id,
            user_id=g.user_id,
            include_all=True
        )
        
        if success:
            return success_response(data=result.get('group'))
        else:
            status = 403 if 'member' in result.get('error', '').lower() else 404
            return error_response(result.get('error'), status)
            
    except Exception as e:
        logger.error("Get group error: %s", e)
        return error_response('Failed to get group', 500)


@groups_bp.route('/groups/<group_id>', methods=['PUT'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
@require_group_role('admin')
@validate_schema(UpdateTravelGroupSchema)
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
        from app.trips.services.travel_group_service import group_service
        
        data = g.validated_data
        
        success, result = group_service.update_group(
            group_id=group_id,
            user_id=g.user_id,
            **data
        )
        
        if success:
            _invalidate_gp_caches()
            return success_response(data=result.get('group'))
        else:
            status = result.get('status', 400)
            return error_response(result.get('error'), status)
            
    except Exception as e:
        logger.error("Update group error: %s", e)
        return error_response('Failed to update group', 500)


@groups_bp.route('/groups/<group_id>', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
@require_auth
@require_group_role('creator')
def delete_group(group_id):
    """
    Delete a group (creator only)
    
    Request:
        DELETE /api/v2/group-planner/groups/<group_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.trips.services.travel_group_service import group_service
        
        success, result = group_service.delete_group(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if success:
            _invalidate_gp_caches()
            return success_response(message=result.get('message'))
        else:
            status = 403 if 'creator' in result.get('error', '').lower() else 404
            return error_response(result.get('error'), status)
            
    except Exception as e:
        logger.error("Delete group error: %s", e)
        return error_response('Failed to delete group', 500)


@groups_bp.route('/groups/<group_id>/itinerary-document', methods=['PUT'])
@groups_bp.route('/groups/<group_id>/itinerary', methods=['PUT'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
@validate_schema(UpdateItineraryDocumentSchema)
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
        from app.trips.services.travel_group_service import group_service
        
        data = g.validated_data
        content = data.get('content') or data.get('itinerary_document') or ''
        
        success, result = group_service.update_itinerary_document(
            group_id=group_id,
            user_id=g.user_id,
            content=content,
            expected_version=data.get('expected_version')
        )
        
        if success:
            _invalidate_gp_caches()
            return success_response(data=result)
        else:
            status = result.get('status', 400)
            return error_response(result.get('error'), status)
            
    except Exception as e:
        logger.error("Update itinerary document error: %s", e)
        return error_response('Failed to update itinerary document', 500)


@groups_bp.route('/groups/<group_id>/members/<member_id>', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
@require_auth
@require_group_role('admin')
def remove_member(group_id, member_id):
    """
    Remove a member from group (creator only)
    
    Request:
        DELETE /api/v2/group-planner/groups/<group_id>/members/<member_id>
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.trips.services.travel_group_service import group_service
        
        success, result = group_service.remove_member(
            group_id=group_id,
            member_id=member_id,
            requester_id=g.user_id
        )
        
        if success:
            _invalidate_gp_caches()
            return success_response(message=result.get('message'))
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error("Remove member error: %s", e)
        return error_response('Failed to remove member', 500)


@groups_bp.route('/groups/<group_id>/members/<member_id>/role', methods=['PATCH'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
@require_group_role('admin')
def update_member_role(group_id, member_id):
    """
    Update a member's role

    Request:
        PATCH /api/v2/group-planner/groups/<group_id>/members/<member_id>/role
        Headers: Authorization: Bearer <token>
        Body: { "role": "admin" | "member" | "viewer" }
    """
    try:
        from app.trips.services.travel_group_service import group_service

        data = request.get_json(silent=True) or {}
        new_role = data.get('role', '').strip().lower()
        if not new_role:
            return error_response('role is required', 400)

        success, result = group_service.update_member_role(
            group_id=group_id,
            member_id=member_id,
            new_role=new_role,
            requester_id=g.user_id
        )

        if success:
            _invalidate_gp_caches()
            return success_response(data=result.get('member'))
        else:
            return error_response(result.get('error'), 400)

    except Exception as e:
        logger.error("Update member role error: %s", e)
        return error_response('Failed to update member role', 500)



@groups_bp.route('/groups/<group_id>/budget', methods=['PUT', 'PATCH'])
@limit_api(Config.RATE_LIMITS['update'])
@require_auth
@require_group_role('admin')
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
        from app.trips.services.travel_group_service import group_service
        
        data = request.get_json(silent=True)
        
        validated, errors = validate_request(UpdateBudgetSchema, data)
        if errors:
            return validation_error_response(errors)
        
        success, result = group_service.update_budget(
            group_id=group_id,
            user_id=g.user_id,
            estimated_budget=validated['estimated_budget'],
            budget_currency=validated.get('budget_currency')
        )
        
        if success:
            _invalidate_gp_caches()
            return success_response(data=result)
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error("Update budget error: %s", e)
        return error_response('Failed to update budget', 500)


@groups_bp.route('/groups/<group_id>/expense-summary', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_groups:expense_summary', ttl=Config.CACHE_TTLS['expense_summary'], vary_on_user=True)
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
        from app.trips.services.travel_group_service import group_service
        
        success, result = group_service.get_expense_summary(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if success:
            return success_response(data=result)
        else:
            return error_response(result.get('error'))
            
    except Exception as e:
        logger.error("Get expense summary error: %s", e)
        return error_response('Failed to get expense summary', 500)


@groups_bp.route('/groups/<group_id>/link-expense', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
@require_group_role('admin')
def link_expense_group(group_id):
    """
    Link travel group to expense engine group
    Creates a new expense group with same members
    
    Request:
        POST /api/v2/group-planner/groups/<group_id>/link-expense
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.expenses.services.expense_group_service import \
            GroupServiceSQL as expense_group_service_cls
        expense_group_service = expense_group_service_cls()

        from app.trips.services.travel_group_service import group_service

        # First get the travel group to get its details
        success, result = group_service.get_group(
            group_id=group_id,
            user_id=g.user_id,
            include_all=True
        )
        
        if not success:
            return error_response(result.get('error'))
        
        group_data = result.get('group', {})
        
        # Check if already linked
        if group_data.get('expense_group_id'):
            return success_response(
                data={'expense_group_id': group_data['expense_group_id']},
                message='Already linked'
            )
        
        # Create expense group
        expense_success, expense_result = expense_group_service.create_group(
            user_id=g.user_id,
            name=group_data.get('name'),
            description=f"Linked from Group Planner - {group_data.get('destination', 'Trip')}",
            currency=Config.DEFAULT_CURRENCY
        )
        
        if not expense_success:
            logger.error("Failed to create expense group: %s", expense_result)
            return error_response('Failed to create expense group', 500)
        
        expense_group_id = expense_result.get('group', {}).get('id')
        if not expense_group_id:
            logger.error('Expense-group creation returned no group ID: %s', expense_result)
            return error_response('Failed to create expense group', 500)
        logger.info("Created expense group %s for travel group %s", expense_group_id, group_id)

        def remove_unlinked_expense_group():
            """Compensate a partially-created expense group on link failure."""
            removed, removal_result = expense_group_service.delete_group(
                group_id=expense_group_id,
                user_id=g.user_id,
            )
            if not removed:
                logger.error(
                    'Could not clean up unlinked expense group %s: %s',
                    expense_group_id, removal_result.get('error'),
                )
        
        # Add existing members to expense group
        members = group_data.get('member_details', [])
        added_count = 0
        for member in members:
            member_user_id = member.get('user_id')
            member_email = member.get('email')
            
            # Skip the creator (they're already added as admin)
            if not member_user_id or str(member_user_id) == str(g.user_id):
                continue
            if not member_email:
                remove_unlinked_expense_group()
                return error_response('Travel group member is missing an email address', 400)
            try:
                add_success, add_result = expense_group_service.add_member(
                    group_id=expense_group_id,
                    user_id=g.user_id,
                    member_email=member_email,
                    role='member'
                )
            except Exception as exc:
                logger.exception('Error adding member %s to linked expense group', member_email)
                remove_unlinked_expense_group()
                return error_response('Failed to synchronize expense-group members', 500)
            if not add_success:
                logger.error('Could not add member %s: %s', member_email, add_result.get('error'))
                remove_unlinked_expense_group()
                return error_response('Failed to synchronize expense-group members', 400)
            added_count += 1
            logger.info("Added member %s to expense group", member_email)
        
        logger.info("Added %s members to expense group %s", added_count, expense_group_id)
        
        # Link the groups
        link_success, link_result = group_service.link_expense_group(
            group_id=group_id,
            user_id=g.user_id,
            expense_group_id=expense_group_id
        )
        
        if link_success:
            _invalidate_gp_caches()
            return success_response(data={
                'expense_group_id': expense_group_id,
                'members_added': added_count
            })
        else:
            remove_unlinked_expense_group()
            return error_response(link_result.get('error'), link_result.get('status_code', 400))
            
    except Exception as e:
        logger.error("Link expense group error: %s", e)
        return error_response('Failed to link expense group', 500)


@groups_bp.route('/groups/<group_id>/unlink-expense', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
@require_group_role('admin')
def unlink_expense_group(group_id):
    """
    Unlink travel group from expense engine group
    
    Request:
        POST /api/v2/group-planner/groups/<group_id>/unlink-expense
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.trips.services.travel_group_service import group_service
        
        success, result = group_service.unlink_expense_group(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if success:
            _invalidate_gp_caches()
            return success_response(message=result.get('message'))
        else:
            return error_response(result.get('error'), result.get('status_code', 400))
            
    except Exception as e:
        logger.error("Unlink expense group error: %s", e)
        return error_response('Failed to unlink expense group', 500)


@groups_bp.route('/groups/<group_id>/activities', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_groups:activities', ttl=Config.CACHE_TTLS['activities'], vary_on_user=True)
def get_group_activities(group_id):
    """
    Get group activities (paginated)
    
    Request:
        GET /api/v2/group-planner/groups/<group_id>/activities?page=1&per_page=50
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.trips.services.travel_group_service import group_service
        
        page = parse_query_int('page', 1, minimum=1)
        per_page = parse_query_int(
            'per_page', Config.GP_DEFAULT_LIMIT, minimum=1, maximum=100,
        )
        
        success, result = group_service.get_group_activities(
            group_id=group_id,
            user_id=g.user_id,
            page=page,
            per_page=per_page
        )
        
        if success:
            return success_response(
                data=result.get('activities', []),
                pagination=result.get('pagination')
            )
        else:
            return error_response(result.get('error'))
            
    except RequestValidationError:
        raise
    except Exception as e:
        logger.error("Get activities error: %s", e)
        return error_response('Failed to get activities', 500)


# =========================================================================
# MEMBER MANAGEMENT  
# =========================================================================

@groups_bp.route('/groups/<group_id>/members', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
@cache_response(key_prefix='gp_groups:members', ttl=Config.CACHE_TTLS['members'], vary_on_user=True)
def get_group_members(group_id: str):
    """
    Get detailed member list with owner indicator
    
    Request:
        GET /api/v2/group-planner/groups/{group_id}/members
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.trips.services.travel_group_service import group_service
        
        success, result = group_service.get_group_members_detailed(
            group_id=group_id,
            user_id=g.user_id
        )
        
        if not success:
            return error_response(result.get('error', 'Failed to get members'))
        
        return success_response(data=result)
        
    except Exception as e:
        logger.error("Get group members error: %s", e)
        return error_response('Failed to get group members', 500)


@groups_bp.route('/groups/<group_id>/leave', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
def leave_group(group_id: str):
    """
    Leave a group (non-owner members only)

    Request:
        POST /api/v2/group-planner/groups/<group_id>/leave
        Headers: Authorization: Bearer <token>
    """
    try:
        from app.trips.services.travel_group_service import group_service

        success, result = group_service.leave_group(
            group_id=group_id,
            user_id=g.user_id,
        )

        if not success:
            status = 403 if 'owner' in result.get('error', '').lower() else 400
            return error_response(result.get('error'), status)

        _invalidate_gp_caches()
        return success_response(message=result.get('message'))

    except Exception as e:
        logger.error("Leave group error: %s", e)
        return error_response('Failed to leave group', 500)


# =========================================================================
# AUTH VERIFICATION
# =========================================================================

@groups_bp.route('/auth/verify', methods=['POST'])
@limit_api(Config.RATE_LIMITS['read_heavy'])
@require_auth
def verify_auth():
    """
    Verify authentication token
    
    Request:
        POST /api/v2/group-planner/auth/verify
        Headers: Authorization: Bearer <token>
    """
    return success_response(
        message='Authentication verified',
        data={
            'user': {
                'uid': g.user_id,
                'email': g.user_email
            },
            'token': {
                'status': 'valid',
                'present': True
            }
        }
    )


@groups_bp.route('/health', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
def health_check():
    """
    Health check endpoint (no auth required)
    """
    return success_response(data={
        'service': 'Group Planner API (SQL)',
        'version': Config.APP_VERSION,
        'status': 'healthy'
    })
