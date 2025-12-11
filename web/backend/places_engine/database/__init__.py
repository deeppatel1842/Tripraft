"""
Database Initialization Module

Handles Firestore database connection and initialization.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def init_db(settings) -> Optional[object]:
    """
    Initialize Firestore database connection.

    Args:
        settings: Application settings

    Returns:
        Firestore database client or None
    """
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Initialize Firebase if not already done
        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.firebase_credentials)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully")

        # Get Firestore client
        db = firestore.client()
        logger.info("Firestore database client initialized")

        return db

    except ImportError:
        logger.warning("firebase-admin not installed, running in mock mode")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return None
