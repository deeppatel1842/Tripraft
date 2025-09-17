from functools import wraps
from flask import request, jsonify, g
from web.backend.services.firebase.auth_service import auth_service

def login_required(f):
    """
    An auth guard decorator that verifies a Firebase ID token.
    The user's info from the token is attached to Flask's `g` object.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Get the token from the 'Authorization' header
        auth_header = request.headers.get('Authorization')
        id_token = None

        if auth_header and auth_header.startswith('Bearer '):
            id_token = auth_header.split('Bearer ')[1]

        if not id_token:
            return jsonify({'error': 'Authorization token is missing'}), 401

        # 2. Verify the token using your existing service
        user_info = auth_service.verify_token(id_token)

        if not user_info:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # 3. Attach user info to the request context for use in the route
        g.user = user_info

        # 4. If all checks pass, run the original route function
        return f(*args, **kwargs)

    return decorated_function