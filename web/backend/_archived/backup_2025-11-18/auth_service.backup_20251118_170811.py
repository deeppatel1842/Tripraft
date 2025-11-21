"""
Firebase authentication service with user management.

This module uses the project's FirebaseAdmin wrapper instance (firebase_admin_instance)
which lazily initializes the Firebase Admin SDK and exposes `db` and `auth` helpers.
"""
import logging
from firebase_admin import firestore as _firestore
from web.backend.services.firebase.firebase_admin import firebase_admin_instance

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self):
        # firebase_admin_instance lazily initializes the admin SDK when its properties are used
        self.firebase = firebase_admin_instance

    def verify_token(self, id_token: str):
        """Verify Firebase ID token and return a normalized user object or None.

        Returns a dict with safe fields (uid, email, name, picture, email_verified) or None
        if verification fails.
        """
        if not id_token:
            # logger.debug('verify_token called without id_token')
            return None

        try:
            decoded = self.firebase.verify_id_token(id_token, clock_skew_seconds=60)
            if not decoded:
                # logger.debug('verify_id_token returned no decoded token')
                return None

            return {
                'uid': decoded.get('uid'),
                'email': decoded.get('email'),
                'name': decoded.get('name') or decoded.get('firebase', {}).get('sign_in_attributes') or decoded.get('displayName'),
                'picture': decoded.get('picture') or decoded.get('photo_url'),
                'email_verified': decoded.get('email_verified', False)
            }
        except Exception as exc:
            logger.exception('Error verifying ID token: %s', exc)
            return None

    def get_user_profile(self, uid: str):
        """Get user profile from Firestore. Returns dict or None."""
        try:
            db = self.firebase.db
            user_ref = db.collection('users').document(uid)
            user_doc = user_ref.get()
            if user_doc and user_doc.exists:
                return user_doc.to_dict()
            return None
        except Exception as exc:
            logger.exception('Error getting user profile for %s: %s', uid, exc)
            return None

    def create_user_profile(self, uid: str, user_data: dict):
        """Create or update user profile in Firestore. Returns True on success."""
        try:
            db = self.firebase.db
            user_ref = db.collection('users').document(uid)
            now_ts = _firestore.SERVER_TIMESTAMP
            payload = {
                'uid': uid,
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'picture': user_data.get('picture'),
                'created_at': now_ts,
                'updated_at': now_ts,
                'email_verified': user_data.get('email_verified', False)
            }
            user_ref.set(payload, merge=True)
            return True
        except Exception as exc:
            logger.exception('Error creating/updating user profile for %s: %s', uid, exc)
            return False

    def update_user_profile(self, uid: str, updates: dict):
        """Update user profile in Firestore. Returns True on success."""
        try:
            db = self.firebase.db
            user_ref = db.collection('users').document(uid)
            updates = dict(updates) if updates else {}
            updates['updated_at'] = _firestore.SERVER_TIMESTAMP
            user_ref.update(updates)
            return True
        except Exception as exc:
            logger.exception('Error updating user profile for %s: %s', uid, exc)
            return False


# Global auth service instance
auth_service = AuthService()