"""
Firebase Admin SDK initialization and configuration.
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, auth, firestore
from dotenv import load_dotenv

# Load environment variables from root directory
root_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
load_dotenv(os.path.join(root_dir, '.env'))

class FirebaseAdmin:
    def __init__(self):
        self._app = None
        self._db = None
        self._auth = None
        self._initialized = False
    
    def initialize(self):
        """Initialize Firebase Admin SDK using service account from environment variables."""
        if self._initialized:
            return
        
        try:
            # Create service account dict from environment variables
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
            
            # Initialize Firebase Admin
            cred = credentials.Certificate(service_account_info)
            self._app = firebase_admin.initialize_app(cred, {
                'projectId': os.getenv("FIREBASE_PROJECT_ID")
            })
            
            self._db = firestore.client()
            self._auth = auth
            self._initialized = True
            
            print(f"Firebase Admin initialized successfully for project: {os.getenv('FIREBASE_PROJECT_ID')}")
            
        except Exception as e:
            print(f"Error initializing Firebase Admin: {str(e)}")
            raise
    
    @property
    def db(self):
        """Get Firestore client."""
        if not self._initialized:
            self.initialize()
        return self._db
    
    @property
    def auth(self):
        """Get Auth client."""
        if not self._initialized:
            self.initialize()
        return self._auth
    
    def verify_id_token(self, id_token):
        """Verify Firebase ID token."""
        try:
            decoded_token = self.auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            print(f"Error verifying ID token: {str(e)}")
            return None
    
    def get_user_by_uid(self, uid):
        """Get user by UID."""
        try:
            user = self.auth.get_user(uid)
            return user
        except Exception as e:
            print(f"Error getting user by UID: {str(e)}")
            return None
    
    def create_user(self, email, password, display_name=None):
        """Create a new user."""
        try:
            user = self.auth.create_user(
                email=email,
                password=password,
                display_name=display_name
            )
            return user
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            return None

# Global Firebase instance
firebase_admin_instance = FirebaseAdmin()