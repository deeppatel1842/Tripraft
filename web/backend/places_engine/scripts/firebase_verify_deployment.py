#!/usr/bin/env python3
"""
Firebase Deployment Verification Script

Verifies that Places Engine data has been successfully deployed to Firebase Firestore.
Checks data integrity, performs test queries, and validates performance.

Usage:
    python scripts/firebase_verify_deployment.py

Environment Variables:
    FIREBASE_CREDENTIALS_PATH: Path to Firebase service account JSON key
    FIREBASE_PROJECT_ID: Firebase project ID
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FirebaseVerifier:
    """Verifies Places Engine deployment in Firestore."""

    def __init__(self):
        """Initialize the verifier."""
        self.db = None
        self.results = {
            'collections_checked': 0,
            'documents_found': {},
            'sample_documents': {},
            'query_tests': {},
            'performance_metrics': {},
            'errors': []
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

    def check_collection(self, collection_name: str, expected_docs: int = None) -> bool:
        """
        Check if a collection exists and has documents.

        Args:
            collection_name: Name of collection to check
            expected_docs: Expected minimum number of documents

        Returns:
            True if collection exists and has data
        """
        try:
            logger.info(f"\nChecking collection: {collection_name}")

            # Get collection stats
            docs = self.db.collection(collection_name).limit(101).get()
            doc_list = list(docs)
            doc_count = len(doc_list)

            logger.info(f"  Documents found: {doc_count}")

            self.results['collections_checked'] += 1
            self.results['documents_found'][collection_name] = doc_count

            # Store sample document
            if doc_list:
                sample_doc = doc_list[0].to_dict()
                self.results['sample_documents'][collection_name] = sample_doc
                logger.info(f"  Sample document keys: {list(sample_doc.keys())}")

            # Validate count
            if expected_docs and doc_count < expected_docs:
                logger.warning(f"  ⚠️  Expected at least {expected_docs} documents")
                self.results['errors'].append(
                    f"{collection_name}: Expected {expected_docs}, found {doc_count}"
                )
                return False

            logger.info(f"  ✅ Collection '{collection_name}' verified")
            return True

        except Exception as e:
            logger.error(f"  ✗ Error checking {collection_name}: {str(e)}")
            self.results['errors'].append(f"Collection check error: {str(e)}")
            return False

    def test_search_query(self, collection: str, field: str, value: str) -> Tuple[int, float]:
        """
        Test a search query for performance.

        Args:
            collection: Collection name
            field: Field to search
            value: Search value

        Returns:
            Tuple of (result_count, query_time_ms)
        """
        try:
            start_time = time.time()
            docs = self.db.collection(collection).where(
                field, '==', value
            ).limit(10).get()
            query_time = (time.time() - start_time) * 1000  # Convert to ms

            result_count = len(list(docs))
            return result_count, query_time

        except Exception as e:
            logger.warning(f"  Query error: {str(e)}")
            return 0, 0

    def verify_countries(self) -> bool:
        """Verify countries collection."""
        if not self.check_collection('countries', 80):
            return False

        # Test query
        start = time.time()
        docs = self.db.collection('countries').limit(5).get()
        query_time = (time.time() - start) * 1000

        self.results['query_tests']['countries_sample'] = {
            'query': 'Sample countries (limit 5)',
            'time_ms': query_time,
            'status': '✅ OK' if query_time < 100 else '⚠️ Slow'
        }

        logger.info(f"  Query time (sample): {query_time:.2f}ms")
        return True

    def verify_states(self) -> bool:
        """Verify states collection."""
        if not self.check_collection('states', 800):
            return False

        # Test query
        start = time.time()
        docs = self.db.collection('states').limit(5).get()
        query_time = (time.time() - start) * 1000

        self.results['query_tests']['states_sample'] = {
            'query': 'Sample states (limit 5)',
            'time_ms': query_time,
            'status': '✅ OK' if query_time < 100 else '⚠️ Slow'
        }

        logger.info(f"  Query time (sample): {query_time:.2f}ms")
        return True

    def verify_cities(self) -> bool:
        """Verify cities collection."""
        if not self.check_collection('cities', 750):
            return False

        # Test query
        start = time.time()
        docs = self.db.collection('cities').limit(5).get()
        query_time = (time.time() - start) * 1000

        self.results['query_tests']['cities_sample'] = {
            'query': 'Sample cities (limit 5)',
            'time_ms': query_time,
            'status': '✅ OK' if query_time < 100 else '⚠️ Slow'
        }

        logger.info(f"  Query time (sample): {query_time:.2f}ms")
        return True

    def verify_search_index(self) -> bool:
        """Verify search index collection."""
        if not self.check_collection('search_index', 1000):
            return False

        # Test query
        start = time.time()
        docs = self.db.collection('search_index').limit(5).get()
        query_time = (time.time() - start) * 1000

        self.results['query_tests']['search_index_sample'] = {
            'query': 'Sample search index (limit 5)',
            'time_ms': query_time,
            'status': '✅ OK' if query_time < 100 else '⚠️ Slow'
        }

        logger.info(f"  Query time (sample): {query_time:.2f}ms")
        return True

    def verify_data_integrity(self) -> bool:
        """Verify data integrity and structure."""
        logger.info("\n" + "="*80)
        logger.info("VERIFYING DATA INTEGRITY")
        logger.info("="*80)

        all_ok = True

        # Check countries
        if self.results['sample_documents'].get('countries'):
            country = self.results['sample_documents']['countries']
            required_fields = ['id', 'name', 'country_normalized']
            missing = [f for f in required_fields if f not in country]
            if missing:
                logger.warning(f"  ⚠️  Countries missing fields: {missing}")
                all_ok = False
            else:
                logger.info(f"  ✅ Countries have required fields")

        # Check states
        if self.results['sample_documents'].get('states'):
            state = self.results['sample_documents']['states']
            required_fields = ['id', 'name', 'country_id']
            missing = [f for f in required_fields if f not in state]
            if missing:
                logger.warning(f"  ⚠️  States missing fields: {missing}")
                all_ok = False
            else:
                logger.info(f"  ✅ States have required fields")

        # Check cities
        if self.results['sample_documents'].get('cities'):
            city = self.results['sample_documents']['cities']
            required_fields = ['id', 'name', 'country_id']
            missing = [f for f in required_fields if f not in city]
            if missing:
                logger.warning(f"  ⚠️  Cities missing fields: {missing}")
                all_ok = False
            else:
                logger.info(f"  ✅ Cities have required fields")

        return all_ok

    def verify(self) -> bool:
        """Execute full verification."""
        logger.info("\n" + "█"*80)
        logger.info("█  FIREBASE DEPLOYMENT VERIFICATION")
        logger.info("█"*80)

        # Initialize Firebase
        config = self.load_firebase_config()
        self.db = self.initialize_firebase(config)

        logger.info("✅ Firebase initialized successfully")

        # Verify collections
        logger.info("\n" + "="*80)
        logger.info("VERIFYING COLLECTIONS")
        logger.info("="*80)

        all_verified = True
        all_verified &= self.verify_countries()
        all_verified &= self.verify_states()
        all_verified &= self.verify_cities()
        all_verified &= self.verify_search_index()

        # Verify data integrity
        all_verified &= self.verify_data_integrity()

        # Print summary
        self.print_summary()

        return all_verified

    def print_summary(self):
        """Print verification summary."""
        logger.info("\n" + "="*80)
        logger.info("VERIFICATION SUMMARY")
        logger.info("="*80)

        logger.info(f"\n📊 COLLECTIONS CHECKED: {self.results['collections_checked']}")
        logger.info("\n📈 DOCUMENTS FOUND:")

        total_docs = 0
        for collection, count in self.results['documents_found'].items():
            logger.info(f"  {collection:20} {count:>6} documents")
            total_docs += count

        logger.info(f"  {'-'*34}")
        logger.info(f"  {'TOTAL':20} {total_docs:>6} documents")

        logger.info("\n⚡ QUERY PERFORMANCE:")
        for test_name, test_result in self.results['query_tests'].items():
            time_ms = test_result['time_ms']
            status = test_result['status']
            logger.info(f"  {test_name:30} {time_ms:>6.2f}ms {status}")

        if self.results['errors']:
            logger.info(f"\n⚠️  ERRORS FOUND ({len(self.results['errors'])}):")
            for error in self.results['errors'][:10]:
                logger.info(f"  - {error}")

        logger.info("\n" + "="*80)

        if not self.results['errors']:
            logger.info("✅ VERIFICATION SUCCESSFUL - All checks passed!")
            logger.info("\n✅ Places Engine is ready for production use")
        else:
            logger.warning(f"⚠️  VERIFICATION COMPLETED WITH {len(self.results['errors'])} ERROR(S)")

        logger.info("="*80)


def main():
    """Main execution."""
    verifier = FirebaseVerifier()
    success = verifier.verify()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
