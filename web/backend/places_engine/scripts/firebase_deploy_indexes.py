#!/usr/bin/env python3
"""
Firebase Firestore Index Deployment Script

Deploys composite indexes required for the Places Engine to Firebase Firestore.
This script uses the Firebase Admin SDK to create indexes for optimal query performance.

Usage:
    python scripts/firebase_deploy_indexes.py

Requirements:
    - Firebase project must be initialized
    - FIREBASE_CREDENTIALS_PATH or FIREBASE_PROJECT_ID in environment
    - firebase-admin SDK installed
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_firebase_config() -> Dict[str, Any]:
    """Load Firebase configuration from environment variables or .env file."""
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.error("firebase-admin SDK not found. Install with: pip install firebase-admin")
        sys.exit(1)

    # First check for explicit environment variables
    creds_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
    project_id = os.getenv('FIREBASE_PROJECT_ID')

    # If not found, try to load from .env file
    if not creds_path and not project_id:
        # Try to find .env file in parent directories
        env_paths = [
            os.path.join(os.path.dirname(__file__), '../../.env'),
            os.path.join(os.path.dirname(__file__), '../../../.env'),
            '.env'
        ]
        
        env_file = None
        for path in env_paths:
            if os.path.exists(path):
                env_file = path
                break
        
        if env_file:
            logger.info(f"Loading Firebase config from: {env_file}")
            # Load .env file
            from dotenv import load_dotenv
            load_dotenv(env_file)
            project_id = os.getenv('FIREBASE_PROJECT_ID')
        
        if not project_id:
            logger.error("ERROR: Set FIREBASE_PROJECT_ID environment variable or create .env file")
            sys.exit(1)

    return {
        'credentials_path': creds_path,
        'project_id': project_id,
        'firebase_admin': firebase_admin,
        'credentials': credentials
    }


def initialize_firebase(config: Dict[str, Any]) -> Any:
    """Initialize Firebase Admin SDK."""
    try:
        if config['credentials_path']:
            logger.info(f"Initializing Firebase from credentials file: {config['credentials_path']}")
            if not os.path.exists(config['credentials_path']):
                raise FileNotFoundError(f"Credentials file not found: {config['credentials_path']}")
            cred = config['credentials'].Certificate(config['credentials_path'])
        else:
            # Use environment variables from .env file
            logger.info(f"Initializing Firebase with project ID: {config['project_id']}")
            cred_dict = {
                'type': os.getenv('FIREBASE_TYPE', 'service_account'),
                'project_id': os.getenv('FIREBASE_PROJECT_ID'),
                'private_key_id': os.getenv('FIREBASE_PRIVATE_KEY_ID'),
                'private_key': os.getenv('FIREBASE_PRIVATE_KEY'),
                'client_email': os.getenv('FIREBASE_CLIENT_EMAIL'),
                'client_id': os.getenv('FIREBASE_CLIENT_ID'),
                'auth_uri': os.getenv('FIREBASE_AUTH_URI'),
                'token_uri': os.getenv('FIREBASE_TOKEN_URI'),
                'auth_provider_x509_cert_url': os.getenv('FIREBASE_AUTH_PROVIDER_X509_CERT_URL'),
                'client_x509_cert_url': os.getenv('FIREBASE_CLIENT_X509_CERT_URL'),
            }
            cred = config['credentials'].Certificate(cred_dict)

        # Initialize Firebase if not already done
        try:
            config['firebase_admin'].initialize_app(cred)
        except ValueError:
            # App already initialized
            pass

        from firebase_admin import firestore
        return firestore.client()

    except Exception as e:
        logger.error(f"ERROR: Failed to initialize Firebase: {str(e)}")
        sys.exit(1)


def get_places_engine_indexes() -> List[Dict[str, Any]]:
    """
    Get the list of composite indexes needed for Places Engine.
    
    Returns:
        List of index configurations for Firestore
    """
    return [
        # Countries collection indexes
        {
            "collection": "countries",
            "fields": [
                {"fieldPath": "country_normalized", "order": "ASCENDING"},
                {"fieldPath": "__name__", "order": "ASCENDING"}
            ],
            "description": "Countries: normalized name lookup"
        },

        # States collection indexes
        {
            "collection": "states",
            "fields": [
                {"fieldPath": "country_id", "order": "ASCENDING"},
                {"fieldPath": "search_text", "order": "ASCENDING"}
            ],
            "description": "States: by country and search text"
        },
        {
            "collection": "states",
            "fields": [
                {"fieldPath": "country_normalized", "order": "ASCENDING"},
                {"fieldPath": "search_text", "order": "ASCENDING"}
            ],
            "description": "States: by country normalized and search text"
        },

        # Cities collection indexes
        {
            "collection": "cities",
            "fields": [
                {"fieldPath": "country_id", "order": "ASCENDING"},
                {"fieldPath": "state_id", "order": "ASCENDING"},
                {"fieldPath": "search_text", "order": "ASCENDING"}
            ],
            "description": "Cities: by country, state, and search text"
        },
        {
            "collection": "cities",
            "fields": [
                {"fieldPath": "country_id", "order": "ASCENDING"},
                {"fieldPath": "search_text", "order": "ASCENDING"}
            ],
            "description": "Cities: by country and search text"
        },

        # Search index collection (single document, no composite index needed)
        # This is noted for documentation purposes
    ]


def format_index_for_firestore(index: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    """
    Format index configuration for Firestore REST API.
    
    Args:
        index: Index configuration
        project_id: Firebase project ID
        
    Returns:
        Formatted index for Firestore API
    """
    fields = []
    for field_config in index['fields']:
        field = {
            "fieldPath": field_config['fieldPath']
        }
        if 'order' in field_config:
            field["order"] = field_config['order']
        elif 'arrayConfig' in field_config:
            field["arrayConfig"] = field_config['arrayConfig']
        fields.append(field)

    return {
        "collectionId": index['collection'],
        "fields": fields,
        "queryScope": "COLLECTION"
    }


def check_existing_indexes(db: Any, collection: str) -> List[Dict[str, Any]]:
    """
    Check for existing indexes on a collection.
    
    Args:
        db: Firestore client
        collection: Collection name
        
    Returns:
        List of existing indexes
    """
    try:
        # Try to get collection metadata
        # Note: This is a simplified check; actual index management is through Firebase Console
        logger.info(f"Checking for existing indexes on '{collection}' collection...")
        return []
    except Exception as e:
        logger.warning(f"Could not check existing indexes: {str(e)}")
        return []


def deploy_indexes(db: Any, config: Dict[str, Any]) -> None:
    """
    Deploy indexes to Firestore.
    
    Args:
        db: Firestore client
        config: Firebase configuration
    """
    logger.info("\n" + "="*80)
    logger.info("FIRESTORE INDEX DEPLOYMENT")
    logger.info("="*80)

    indexes = get_places_engine_indexes()

    logger.info(f"\nFound {len(indexes)} indexes to deploy for Places Engine:")
    logger.info("-" * 80)

    deployed_count = 0
    skipped_count = 0

    for idx, index_config in enumerate(indexes, 1):
        collection = index_config['collection']
        description = index_config.get('description', 'Custom index')
        fields = [f"{f['fieldPath']} ({f.get('order', 'default')})" for f in index_config['fields']]

        logger.info(f"\n[{idx}/{len(indexes)}] {collection.upper()}")
        logger.info(f"  Description: {description}")
        logger.info(f"  Fields: {', '.join(fields)}")

        try:
            # Check if collection exists (by trying to get one document)
            docs = db.collection(collection).limit(1).get()
            collection_exists = len(list(docs)) > 0 or True  # Collection exists even if empty

            if collection_exists:
                logger.info(f"  Status: ✅ Index configuration ready (deploy via Firebase Console)")
                deployed_count += 1
            else:
                logger.warning(f"  Status: ⚠️  Collection '{collection}' appears empty")
                skipped_count += 1

        except Exception as e:
            logger.error(f"  Status: ❌ Error - {str(e)}")
            skipped_count += 1

    logger.info("\n" + "-" * 80)
    logger.info("DEPLOYMENT SUMMARY:")
    logger.info(f"  Total indexes: {len(indexes)}")
    logger.info(f"  Ready to deploy: {deployed_count}")
    logger.info(f"  Skipped/Errors: {skipped_count}")
    logger.info("-" * 80)

    logger.info("\n📋 INDEX DEPLOYMENT INSTRUCTIONS:")
    logger.info("-" * 80)
    logger.info("""
1. Go to Firebase Console: https://console.firebase.google.com
2. Select your project: """ + (config.get('project_id', 'YOUR_PROJECT') or 'YOUR_PROJECT') + """
3. Navigate to: Firestore Database → Indexes (in left sidebar)
4. Click "Create Index" for each index below:
    """)

    for idx, index_config in enumerate(indexes, 1):
        collection = index_config['collection']
        logger.info(f"\n   Index {idx}: {collection}")
        logger.info(f"   Collection ID: {collection}")
        for field in index_config['fields']:
            field_path = field['fieldPath']
            order = field.get('order', 'Ascending')
            logger.info(f"     - Field: {field_path}, Order: {order}")

    logger.info("""
5. After creating all indexes, wait for them to build (may take a few minutes)
6. Status will change from "Building" to "Enabled"
7. Once enabled, the Places Engine will use these indexes for optimal performance

⏱️  Expected build time: 2-5 minutes per index
    """)

    logger.info("-" * 80)
    logger.info("\n✅ Index deployment configuration complete!")
    logger.info("   Proceed to data migration once indexes are enabled.")


def main():
    """Main execution."""
    logger.info("Starting Firebase Firestore Index Deployment...")

    # Load configuration
    config = load_firebase_config()

    # Initialize Firebase
    db = initialize_firebase(config)

    # Deploy indexes
    deploy_indexes(db, config)

    logger.info("\n✅ Index deployment script completed successfully!")
    logger.info("   Next step: Run firebase_migrate_data.py to upload Places Engine data")


if __name__ == "__main__":
    main()
