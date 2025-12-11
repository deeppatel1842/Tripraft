"""
User Profile Management Routes
Handles user profile CRUD operations and user search
"""

from flask import Blueprint, request, jsonify, g
import logging

from ..service import expense_service
from .route_helpers import require_auth

logger = logging.getLogger(__name__)

# Create blueprint
user_bp = Blueprint('user', __name__)


# =============================================================================
# USER PROFILE ROUTES
# =============================================================================

@user_bp.route('/user/profile', methods=['POST'])
@require_auth
def create_user_profile():
    """
    Create or update user profile
    
    Creates new user profile on first sign-in.
    Returns existing profile if user already exists.
    
    Request Body:
        username (str): Required. Unique username
        display_name (str): Optional. Display name
        profile_picture (str): Optional. Profile picture URL
        
    Returns:
        201: User created successfully
        200: User already exists
        400: Validation error
        500: Server error
    """
    try:
        data = request.get_json()
        
        # Check if user already exists
        existing_user = expense_service.get_user(g.user_id)
        if existing_user:
            # User already registered, return existing profile
            # Note: Auto cache warming disabled (too slow on profile check)
            # Cache warming now happens lazily on first data fetch
            return jsonify({'message': 'User already exists', 'user': existing_user}), 200
        
        # Validate required fields
        if not data.get('username'):
            return jsonify({'error': 'Username is required'}), 400
        
        # Check if username is taken
        username_check = expense_service.get_user_by_username(data['username'])
        if username_check:
            return jsonify({'error': 'Username already taken'}), 400
        
        # Create user
        user = expense_service.create_user(
            uid=g.user_id,
            email=g.user_email,
            username=data['username'],
            display_name=data.get('display_name'),
            profile_picture=data.get('profile_picture')
        )
        
        # Note: Auto cache warming disabled (too slow)
        # Cache warming now happens lazily on first data fetch
        
        return jsonify({'success': True, 'user': user}), 201
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating user profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """
    Get current user profile
    
    Returns authenticated user's profile information.
    
    Returns:
        200: User profile retrieved
        404: User not found
        500: Server error
    """
    try:
        user = expense_service.get_user(g.user_id)
        if not user:
            return jsonify({'error': 'User profile not found'}), 404
        
        return jsonify({'success': True, 'user': user}), 200
    
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/user/profile', methods=['PUT'])
@require_auth
def update_user_profile():
    """
    Update user profile
    
    Updates user profile fields.
    Validates username uniqueness if changing username.
    
    Request Body:
        username (str): Optional. New username
        display_name (str): Optional. New display name
        profile_picture (str): Optional. New profile picture URL
        
    Returns:
        200: Profile updated successfully
        400: Validation error (username taken)
        500: Server error
    """
    try:
        data = request.get_json()
        
        # Validate username if changing
        if 'username' in data:
            existing = expense_service.get_user_by_username(data['username'])
            if existing and existing['uid'] != g.user_id:
                return jsonify({'error': 'Username already taken'}), 400
        
        # Update user
        success = expense_service.update_user(g.user_id, data)
        
        if success:
            user = expense_service.get_user(g.user_id)
            return jsonify({'success': True, 'user': user}), 200
        else:
            return jsonify({'error': 'Failed to update profile'}), 500
    
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# USER SEARCH ROUTES
# =============================================================================

@user_bp.route('/user/search', methods=['GET'])
@require_auth
def search_users():
    """
    Search for users by username or email
    
    Searches for users by username (preferred) or email.
    Returns limited info for privacy (no email in response).
    
    Query Parameters:
        q (str): Required. Search query (username or email)
        
    Returns:
        200: Search completed (user found or not found)
        400: Missing search query
        500: Server error
        
    Response:
        {
            'success': True,
            'user': {
                'uid': '...',
                'username': '...',
                'display_name': '...',
                'profile_picture': '...'
            } or None
        }
    """
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        # Try to find by username first
        user = expense_service.get_user_by_username(query)
        
        # If not found, try email
        if not user:
            user = expense_service.get_user_by_email(query)
        
        if user:
            # Return limited info for privacy
            return jsonify({
                'success': True,
                'user': {
                    'uid': user['uid'],
                    'username': user['username'],
                    'display_name': user['display_name'],
                    'profile_picture': user.get('profile_picture')
                }
            }), 200
        else:
            return jsonify({'success': True, 'user': None}), 200
    
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# PHASE 3: USER SUMMARY ENDPOINT
# =============================================================================

@user_bp.route('/user/summary', methods=['GET'])
@require_auth
def get_user_summary():
    """
    Get user's group summaries (PHASE 3 - Optimized)
    
    Returns lightweight pre-computed summaries for all user's groups.
    This is 90% faster than fetching full group data.
    
    Performance:
    - OLD: get_user_groups() = 100+ reads
    - NEW: get_user_group_summaries() = N reads (one per group)
    
    Query Parameters:
        None
    
    Returns:
        200: Success
        {
            "success": true,
            "groups": [
                {
                    "group_id": "uuid",
                    "group_name": "Seattle Trip",
                    "your_balance": -25.50,
                    "member_count": 5,
                    "expense_count": 42,
                    "total_spent": 1250.00,
                    "currency": "USD",
                    "is_settled": false,
                    "last_activity": "2025-11-24T10:30:00Z"
                }
            ],
            "count": 1
        }
        500: Server error
    """
    try:
        logger.info(f"🚀 PHASE 3: Fetching group summaries for user {g.user_id}")
        
        # Get pre-computed summaries (Phase 3 optimization)
        summaries = expense_service.get_user_group_summaries(g.user_id)
        
        return jsonify({
            'success': True,
            'groups': summaries,
            'count': len(summaries)
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching user summary: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
