#!/usr/bin/env python3
"""
Firebase Data Migration Script for Places Engine

Uploads aggregated Places Engine data (countries, states, cities, search index)
from JSON files to Firebase Firestore with batch processing and error handling.

Usage:
    python scripts/firebase_migrate_data.py

Environment Variables:
    FIREBASE_CREDENTIALS_PATH: Path to Firebase service account JSON key
    FIREBASE_PROJECT_ID: Firebase project ID
    DATA_PATH: Path to aggregated data directory (default: ./pipeline/aggregated_data)

Requirements:
    - firebase-admin SDK installed
    - Firestore indexes deployed
    - Aggregated data files in pipeline/aggregated_data/
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FirebaseDataMigrator:
    """Handles migration of Places Engine data to Firestore."""

    def __init__(self):
        """Initialize the migrator."""
        self.db = None
        self.stats = {
            'countries_uploaded': 0,
            'states_uploaded': 0,
            'cities_uploaded': 0,
            'search_docs_uploaded': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }

    def load_firebase_config(self) -> Dict[str, str]:
        """Load Firebase configuration from environment or .env file."""
        try:
            import firebase_admin
            from firebase_admin import credentials
        except ImportError:
            logger.error("firebase-admin SDK not found. Install with: pip install firebase-admin")
            sys.exit(1)

        # Check for explicit environment variables first
        creds_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
        project_id = os.getenv('FIREBASE_PROJECT_ID')

        # If not found, try to load from .env file
        if not creds_path and not project_id:
            env_paths = [
                os.path.join(os.path.dirname(__file__), '../../.env'),
                os.path.join(os.path.dirname(__file__), '../../../.env'),
                '.env'
            ]
            env_file = next((p for p in env_paths if os.path.exists(p)), None)
            if env_file:
                logger.info(f"Loading Firebase config from: {env_file}")
                try:
                    from dotenv import load_dotenv
                    load_dotenv(env_file)
                    project_id = os.getenv('FIREBASE_PROJECT_ID')
                except ImportError:
                    logger.warning("python-dotenv not found. Install with: pip install python-dotenv")

        if not project_id:
            logger.error("ERROR: FIREBASE_PROJECT_ID not found in environment or .env file")
            sys.exit(1)

        return {
            'firebase_admin': firebase_admin,
            'credentials': credentials,
            'creds_path': creds_path,
            'project_id': project_id
        }

    def initialize_firebase(self, config: Dict) -> Any:
        """Initialize Firebase Admin SDK."""
        try:
            if config['creds_path']:
                logger.info(f"Initializing Firebase from: {config['creds_path']}")
                if not os.path.exists(config['creds_path']):
                    raise FileNotFoundError(f"Credentials file not found: {config['creds_path']}")
                cred = config['credentials'].Certificate(config['creds_path'])
            else:
                # Use environment variables from .env file
                logger.info(f"Initializing Firebase with project: {config['project_id']}")
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

            try:
                config['firebase_admin'].initialize_app(cred)
            except ValueError:
                pass

            from firebase_admin import firestore
            return firestore.client()

        except Exception as e:
            logger.error(f"ERROR: Failed to initialize Firebase: {str(e)}")
            sys.exit(1)

    def load_json_data(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Load JSON data from file.

        Args:
            filepath: Path to JSON file

        Returns:
            Loaded data (list or dict)
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
                return data if isinstance(data, list) else [data]
        except Exception as e:
            logger.error(f"ERROR: Failed to load {filepath}: {str(e)}")
            self.stats['errors'].append(f"Load error: {filepath}")
            return []

    def batch_write(self, collection: str, documents: List[Tuple[str, Dict]], batch_size: int = 500) -> int:
        """
        Write documents to Firestore in batches.

        Args:
            collection: Collection name
            documents: List of (doc_id, doc_data) tuples
            batch_size: Documents per batch (max 500 for Firestore)

        Returns:
            Number of documents successfully written
        """
        written = 0
        total = len(documents)

        for i in range(0, total, batch_size):
            batch = self.db.batch()
            batch_docs = documents[i:i+batch_size]

            try:
                for doc_id, doc_data in batch_docs:
                    batch.set(
                        self.db.collection(collection).document(str(doc_id)),
                        doc_data,
                        merge=False
                    )

                batch.commit()
                written += len(batch_docs)
                logger.info(f"  ✓ Batch {i//batch_size + 1}: {written}/{total} documents written")

            except Exception as e:
                logger.error(f"  ✗ Batch error: {str(e)}")
                self.stats['errors'].append(f"Batch write error in {collection}: {str(e)}")
                break

        return written

    def upload_countries(self, data_path: str) -> int:
        """Upload countries data to Firestore."""
        logger.info("\n" + "="*80)
        logger.info("UPLOADING COUNTRIES")
        logger.info("="*80)

        filepath = os.path.join(data_path, 'countries_aggregated.json')
        if not os.path.exists(filepath):
            logger.warning(f"⚠️  Countries file not found: {filepath}")
            return 0

        countries = self.load_json_data(filepath)
        logger.info(f"Loaded {len(countries)} countries")

        if not countries:
            return 0

        # Prepare documents (use country code as doc ID)
        documents = []
        for country in countries:
            if isinstance(country, dict) and 'id' in country:
                doc_id = country['id']
                doc_data = {
                    **country,
                    'timestamp': datetime.now().isoformat(),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                documents.append((doc_id, doc_data))

        logger.info(f"Uploading {len(documents)} countries to Firestore...")
        written = self.batch_write('countries', documents)

        self.stats['countries_uploaded'] = written
        logger.info(f"✅ {written} countries uploaded")
        return written

    def upload_states(self, data_path: str) -> int:
        """Upload states data to Firestore."""
        logger.info("\n" + "="*80)
        logger.info("UPLOADING STATES")
        logger.info("="*80)

        filepath = os.path.join(data_path, 'states_aggregated.json')
        if not os.path.exists(filepath):
            logger.warning(f"⚠️  States file not found: {filepath}")
            return 0

        states = self.load_json_data(filepath)
        logger.info(f"Loaded {len(states)} states")

        if not states:
            return 0

        # Prepare documents
        documents = []
        for state in states:
            if isinstance(state, dict) and 'id' in state:
                doc_id = state['id']
                doc_data = {
                    **state,
                    'timestamp': datetime.now().isoformat(),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                documents.append((doc_id, doc_data))

        logger.info(f"Uploading {len(documents)} states to Firestore...")
        # Use smaller batch size for states due to nested data size
        written = self.batch_write('states', documents, batch_size=50)

        self.stats['states_uploaded'] = written
        logger.info(f"✅ {written} states uploaded")
        return written

    def upload_cities(self, data_path: str) -> int:
        """Upload cities data to Firestore."""
        logger.info("\n" + "="*80)
        logger.info("UPLOADING CITIES")
        logger.info("="*80)

        filepath = os.path.join(data_path, 'cities_aggregated.json')
        if not os.path.exists(filepath):
            logger.warning(f"⚠️  Cities file not found: {filepath}")
            return 0

        cities = self.load_json_data(filepath)
        logger.info(f"Loaded {len(cities)} cities")

        if not cities:
            return 0

        # Prepare documents
        documents = []
        for city in cities:
            if isinstance(city, dict) and 'id' in city:
                doc_id = city['id']
                doc_data = {
                    **city,
                    'timestamp': datetime.now().isoformat(),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                documents.append((doc_id, doc_data))

        logger.info(f"Uploading {len(documents)} cities to Firestore...")
        # Use smaller batch size for cities due to nested data size
        written = self.batch_write('cities', documents, batch_size=50)

        self.stats['cities_uploaded'] = written
        logger.info(f"✅ {written} cities uploaded")
        return written

    def upload_search_index(self, data_path: str) -> int:
        """Upload search index to Firestore."""
        logger.info("\n" + "="*80)
        logger.info("UPLOADING SEARCH INDEX")
        logger.info("="*80)

        filepath = os.path.join(data_path, 'search_index_documents.json')
        if not os.path.exists(filepath):
            logger.warning(f"⚠️  Search index file not found: {filepath}")
            return 0

        search_docs = self.load_json_data(filepath)
        logger.info(f"Loaded {len(search_docs)} search index documents")

        if not search_docs:
            return 0

        # Prepare documents
        documents = []
        for idx, doc in enumerate(search_docs, 1):
            if isinstance(doc, dict):
                doc_id = f"prefix_{idx:04d}"
                doc_data = {
                    **doc,
                    'timestamp': datetime.now().isoformat(),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                documents.append((doc_id, doc_data))

        logger.info(f"Uploading {len(documents)} search index documents to Firestore...")
        written = self.batch_write('search_index', documents)

        self.stats['search_docs_uploaded'] = written
        logger.info(f"✅ {written} search index documents uploaded")
        return written

    def migrate(self, data_path: str = None) -> bool:
        """
        Execute the full data migration.

        Args:
            data_path: Path to aggregated data directory

        Returns:
            True if successful, False otherwise
        """
        self.stats['start_time'] = datetime.now()

        logger.info("\n" + "█"*80)
        logger.info("█  FIREBASE DATA MIGRATION - PLACES ENGINE")
        logger.info("█"*80)

        # Determine data path
        if not data_path:
            data_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'pipeline',
                'aggregated_data'
            )

        logger.info(f"\nData path: {data_path}")

        if not os.path.exists(data_path):
            logger.error(f"ERROR: Data directory not found: {data_path}")
            return False

        # Initialize Firebase
        config = self.load_firebase_config()
        self.db = self.initialize_firebase(config)

        logger.info("✅ Firebase initialized successfully\n")

        # Upload all data
        try:
            self.upload_countries(data_path)
            self.upload_states(data_path)
            self.upload_cities(data_path)
            self.upload_search_index(data_path)

        except Exception as e:
            logger.error(f"ERROR: Migration failed: {str(e)}")
            self.stats['errors'].append(str(e))
            return False

        # Print summary
        self.print_summary()
        self.stats['end_time'] = datetime.now()

        return len(self.stats['errors']) == 0

    def print_summary(self):
        """Print migration summary."""
        logger.info("\n" + "="*80)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*80)

        logger.info(f"\n📊 DOCUMENTS UPLOADED:")
        logger.info(f"  Countries:        {self.stats['countries_uploaded']:>5}")
        logger.info(f"  States:           {self.stats['states_uploaded']:>5}")
        logger.info(f"  Cities:           {self.stats['cities_uploaded']:>5}")
        logger.info(f"  Search Index:     {self.stats['search_docs_uploaded']:>5}")
        logger.info(f"  {'-'*40}")

        total = (self.stats['countries_uploaded'] + 
                self.stats['states_uploaded'] + 
                self.stats['cities_uploaded'] + 
                self.stats['search_docs_uploaded'])

        logger.info(f"  TOTAL:            {total:>5}")

        if self.stats['errors']:
            logger.info(f"\n⚠️  ERRORS ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:10]:  # Show first 10
                logger.info(f"  - {error}")
            if len(self.stats['errors']) > 10:
                logger.info(f"  ... and {len(self.stats['errors']) - 10} more")

        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            logger.info(f"\n⏱️  Duration: {duration:.2f} seconds")
            if total > 0:
                logger.info(f"   Rate: {total/duration:.0f} docs/second")

        logger.info("\n" + "="*80)

        if len(self.stats['errors']) == 0:
            logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
        else:
            logger.warning("⚠️  MIGRATION COMPLETED WITH ERRORS")

        logger.info("="*80)


def main():
    """Main execution."""
    migrator = FirebaseDataMigrator()

    # Get optional data path argument
    data_path = sys.argv[1] if len(sys.argv) > 1 else None

    # Run migration
    success = migrator.migrate(data_path)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
