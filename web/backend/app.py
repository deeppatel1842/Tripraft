# from flask import Flask, jsonify
# from global_config import DEFAULT_API_PREFIX, APP_NAME
# from web.backend.cache.redis_client import redis_client 
# from web.backend.config import Config

# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)

#     redis_client.init_app(app)

#     # --- Use the global constant ---
#     @app.route(f'{DEFAULT_API_PREFIX}/health')
#     def health():
#         return jsonify({"status": "ok"})

#     @app.route(f'{DEFAULT_API_PREFIX}/config')
#     def get_config():
#         return jsonify({
#             'APP_NAME': APP_NAME,
#             'API_PREFIX': DEFAULT_API_PREFIX,
#         })

#     try:
#         from web.backend.auth import auth_bp
#         # --- Register auth blueprint at /api/auth ---
#         app.register_blueprint(auth_bp, url_prefix=f'{DEFAULT_API_PREFIX}/auth')
#     except Exception as e:
#         print(f"Error registering blueprint: {e}")
#         pass

#     return app

# if __name__ == '__main__':
#     app = create_app()
#     app.run(host='0.0.0.0', port=5000, debug=True)

import os
from flask import Flask, jsonify, request, g
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, auth
from functools import wraps
from dotenv import load_dotenv

# --- Initialization ---
app = Flask(__name__)
CORS(app, supports_credentials=True) 

# Load environment variables from the .env file in the same directory
load_dotenv()

try:
    # 1. Create the credentials dictionary from environment variables
    service_account_info = {
        "type": os.getenv("FIREBASE_TYPE"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
        "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
    }

    # 2. Initialize Firebase Admin using the credentials dictionary
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)
    
except Exception as e:
    print(f"Error initializing Firebase Admin: {e}")
    # This will help you debug if your .env variables are missing or incorrect
    # You can remove this in production


# --- Auth Guard (Middleware) Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        id_token = None
        if auth_header and auth_header.startswith('Bearer '):
            id_token = auth_header.split('Bearer ')[1]

        if not id_token:
            return jsonify({'error': 'Authorization token is missing'}), 401

        try:
            decoded_token = auth.verify_id_token(id_token)
            g.user = decoded_token
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token', 'detail': str(e)}), 401
        
        return f(*args, **kwargs)
    return decorated_function


# --- Routes ---

@app.route('/api/auth/verify', methods=['POST'])
def verify_token():
    """Verifies a Firebase ID token and returns user info."""
    try:
        data = request.get_json()
        id_token = data.get('idToken')

        if not id_token:
            return jsonify({'error': 'ID token is required'}), 400

        decoded_token = auth.verify_id_token(id_token)
        
        uid = decoded_token['uid']
        user_info = {
            'uid': uid,
            'email': decoded_token.get('email'),
            'name': decoded_token.get('name'),
            'picture': decoded_token.get('picture'),
            'email_verified': decoded_token.get('email_verified', False)
        }
        
        return jsonify({'success': True, 'user': user_info}), 200

    except Exception as e:
        return jsonify({'error': 'Token verification failed', 'detail': str(e)}), 401


@app.route('/api/profile', methods=['GET'])
@login_required # <-- This is your middleware in action!
def get_profile():
    user_from_token = g.user
    
    return jsonify({
        'message': 'This is a protected route!',
        'user_uid': user_from_token['uid'],
        'user_email': user_from_token.get('email')
    }), 200


# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)