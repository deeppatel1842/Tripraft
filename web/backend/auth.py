# from flask import Blueprint, jsonify, request, current_app
# from web.backend.services.firebase.auth_service import auth_service
# import logging

# logger = logging.getLogger(__name__)

# auth_bp = Blueprint('auth', __name__)


# # @auth_bp.route('/ping')
# # def ping():
# #     return jsonify({'auth': 'pong'})


# @auth_bp.route('/verify', methods=['POST'])
# def verify_token():
#     """Verify Firebase ID token and return user info."""
#     try:
#         data = request.get_json(silent=True) or {}
#         id_token = data.get('idToken') or data.get('token') or data.get('id_token')

#         if not id_token:
#             return jsonify({'error': 'ID token is required'}), 400

#         user_info = auth_service.verify_token(id_token)

#         if user_info:
#             # Create or update user profile in Firestore (best-effort)
#             try:
#                 auth_service.create_user_profile(user_info['uid'], user_info)
#             except Exception:
#                 logger.exception('Failed to create/update user profile')

#             return jsonify({'success': True, 'user': user_info}), 200
#         else:
#             return jsonify({'error': 'Invalid token'}), 401

#     except Exception as exc:
#         logger.exception('Unexpected error in verify_token: %s', exc)
#         return jsonify({'error': str(exc)}), 500


# @auth_bp.route('/profile/<uid>', methods=['GET'])
# def get_profile(uid):
#     """Get user profile."""
#     try:
#         profile = auth_service.get_user_profile(uid)
#         if profile:
#             return jsonify({'success': True, 'profile': profile})
#         else:
#             return jsonify({'error': 'Profile not found'}), 404
#     except Exception as exc:
#         logger.exception('Error getting profile for %s: %s', uid, exc)
#         return jsonify({'error': str(exc)}), 500


# @auth_bp.route('/profile/<uid>', methods=['PUT'])
# def update_profile(uid):
#     """Update user profile."""
#     try:
#         data = request.get_json(silent=True) or {}
#         success = auth_service.update_user_profile(uid, data)

#         if success:
#             return jsonify({'success': True}), 200
#         else:
#             return jsonify({'error': 'Failed to update profile'}), 500
#     except Exception as exc:
#         logger.exception('Error updating profile for %s: %s', uid, exc)
#         return jsonify({'error': str(exc)}), 500

# # from flask import Blueprint, jsonify, request, current_app
# # from web.backend.services.firebase.auth_service import auth_service
# # import logging

# # logger = logging.getLogger(__name__)

# # auth_bp = Blueprint('auth', __name__)


# # @auth_bp.route('/ping')
# # def ping():
# #     """
# #     Ping the Authentication Blueprint
# #     A simple endpoint to confirm that the auth blueprint is registered and reachable.
# #     ---
# #     tags:
# #       - Authentication
# #     responses:
# #       200:
# #         description: Service is active.
# #         schema:
# #           properties:
# #             auth:
# #               type: string
# #               default: pong
# #     """
# #     return jsonify({'auth': 'pong'})


# # @auth_bp.route('/verify', methods=['POST'])
# # def verify_token():
# #     """
# #     Verify a Firebase ID Token
# #     Receives a Firebase ID token, verifies it, and creates a user profile if one doesn't exist.
# #     ---
# #     tags:
# #       - Authentication
# #     parameters:
# #       - in: body
# #         name: body
# #         required: true
# #         schema:
# #           id: AuthToken
# #           required:
# #             - idToken
# #           properties:
# #             idToken:
# #               type: string
# #               description: The Firebase JWT ID token obtained from the client-side authentication.
# #     responses:
# #       200:
# #         description: Token is valid and user profile is created/retrieved.
# #         schema:
# #           properties:
# #             success:
# #               type: boolean
# #             user:
# #               type: object
# #               description: User information decoded from the token.
# #       400:
# #         description: Bad Request - ID token was not provided in the request body.
# #       401:
# #         description: Unauthorized - The provided token is invalid or expired.
# #       500:
# #         description: Internal Server Error - An unexpected error occurred.
# #     """
# #     try:
# #         data = request.get_json(silent=True) or {}
# #         id_token = data.get('idToken') or data.get('token') or data.get('id_token')

# #         if not id_token:
# #             return jsonify({'error': 'ID token is required'}), 400

# #         user_info = auth_service.verify_token(id_token)

# #         if user_info:
# #             # Create or update user profile in Firestore (best-effort)
# #             try:
# #                 auth_service.create_user_profile(user_info['uid'], user_info)
# #             except Exception:
# #                 logger.exception('Failed to create/update user profile')

# #             return jsonify({'success': True, 'user': user_info}), 200
# #         else:
# #             return jsonify({'error': 'Invalid token'}), 401

# #     except Exception as exc:
# #         logger.exception('Unexpected error in verify_token: %s', exc)
# #         return jsonify({'error': str(exc)}), 500


# # @auth_bp.route('/profile/<uid>', methods=['GET'])
# # def get_profile(uid):
# #     """
# #     Get a User Profile
# #     Retrieves a user's profile information from Firestore using their UID.
# #     ---
# #     tags:
# #       - User Profile
# #     parameters:
# #       - in: path
# #         name: uid
# #         type: string
# #         required: true
# #         description: The unique ID of the user (Firebase UID).
# #     responses:
# #       200:
# #         description: User profile found and returned.
# #         schema:
# #           properties:
# #             success:
# #               type: boolean
# #             profile:
# #               type: object
# #               description: The user's profile data from Firestore.
# #       404:
# #         description: Not Found - A profile with the specified UID does not exist.
# #       500:
# #         description: Internal Server Error - An unexpected error occurred.
# #     """
# #     try:
# #         profile = auth_service.get_user_profile(uid)
# #         if profile:
# #             return jsonify({'success': True, 'profile': profile})
# #         else:
# #             return jsonify({'error': 'Profile not found'}), 404
# #     except Exception as exc:
# #         logger.exception('Error getting profile for %s: %s', uid, exc)
# #         return jsonify({'error': str(exc)}), 500


# # @auth_bp.route('/profile/<uid>', methods=['PUT'])
# # def update_profile(uid):
# #     """
# #     Update a User Profile
# #     Updates a user's profile information in Firestore.
# #     ---
# #     tags:
# #       - User Profile
# #     parameters:
# #       - in: path
# #         name: uid
# #         type: string
# #         required: true
# #         description: The unique ID of the user (Firebase UID) whose profile is to be updated.
# #       - in: body
# #         name: body
# #         required: true
# #         schema:
# #           id: UserProfileUpdate
# #           properties:
# #             displayName:
# #               type: string
# #               description: The user's new display name.
# #             photoURL:
# #               type: string
# #               description: A new URL for the user's profile picture.
# #     responses:
# #       200:
# #         description: The profile was updated successfully.
# #       500:
# #         description: Internal Server Error - The profile update failed.
# #     """
# #     try:
# #         data = request.get_json(silent=True) or {}
# #         success = auth_service.update_user_profile(uid, data)

# #         if success:
# #             return jsonify({'success': True}), 200
# #         else:
# #             return jsonify({'error': 'Failed to update profile'}), 500
# #     except Exception as exc:
# #         logger.exception('Error updating profile for %s: %s', uid, exc)
# #         return jsonify({'error': str(exc)}), 500


from flask import Blueprint, jsonify, request, g
from web.backend.services.firebase.auth_service import auth_service
from web.backend.utils.login_middleware import login_required
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/ping')
def ping():
    return jsonify({'auth': 'pong'})

@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """Verify Firebase ID token and return user info."""
    try:
        data = request.get_json(silent=True) or {}
        id_token = data.get('idToken') or data.get('token') or data.get('id_token')

        if not id_token:
            return jsonify({'error': 'ID token is required'}), 400

        user_info = auth_service.verify_token(id_token)

        if user_info:
            # Create or update user profile in Firestore (best-effort)
            try:
                auth_service.create_user_profile(user_info['uid'], user_info)
            except Exception:
                logger.exception('Failed to create/update user profile')

            return jsonify({'success': True, 'user': user_info}), 200
        else:
            return jsonify({'error': 'Token verification failed'}), 401

    except Exception as exc:
        logger.exception('Unexpected error in verify_token: %s', exc)
        return jsonify({'error': str(exc)}), 500

# --- PROTECTED ROUTES ---

# This route now gets the currently logged-in user's profile
@auth_bp.route('/profile', methods=['GET'])
@login_required # <-- Apply the auth guard
def get_my_profile():
    """Get the current user's profile."""
    try:
        # Get the UID from the token, not the URL
        uid = g.user['uid']
        profile = auth_service.get_user_profile(uid)
        if profile:
            return jsonify({'success': True, 'profile': profile})
        else:
            return jsonify({'error': 'Profile not found'}), 404
    except Exception as exc:
        logger.exception('Error getting profile for %s: %s', g.user.get('uid'), exc)
        return jsonify({'error': str(exc)}), 500


# This route now updates the currently logged-in user's profile
@auth_bp.route('/profile', methods=['PUT'])
@login_required # <-- Apply the auth guard
def update_my_profile():
    """Update the current user's profile."""
    try:
        # Get the UID from the token, not the URL
        uid = g.user['uid']
        data = request.get_json(silent=True) or {}
        success = auth_service.update_user_profile(uid, data)

        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to update profile'}), 500
    except Exception as exc:
        logger.exception('Error updating profile for %s: %s', g.user.get('uid'), exc)
        return jsonify({'error': str(exc)}), 500