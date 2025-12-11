"""
Places Engine Firestore Uploader

Uploads prepared place data to Firebase Firestore.

Features:
- Batch uploads (500 docs at a time)
- Progress tracking
- Error handling with retry logic
- Dry-run mode
- Creates places, cities, countries collections

Usage:
    from places_engine.pipeline import FirestoreUploader
    
    uploader = FirestoreUploader(prepared_data_path='prepared_data')
    uploader.run()
"""

import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    # Try to find .env in web/backend/ directory
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from {env_path}")
    else:
        # Also try project root
        env_path = Path(__file__).parent.parent.parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded environment from {env_path}")
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Optional firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    from google.cloud.firestore_v1 import GeoPoint
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    credentials = None
    firestore = None
    GeoPoint = None


class FirestoreUploader:
    """
    Uploads prepared places data to Firestore.
    
    Handles batch operations, retries, and progress tracking.
    """
    
    BATCH_SIZE = 20  # Very small batches for free tier
    RETRY_COUNT = 5
    RETRY_DELAY = 120.0  # 2 minutes for quota recovery
    BATCH_DELAY = 3.0  # 3 seconds between batches
    
    def __init__(
        self,
        prepared_data_path: str = 'prepared_data',
        credentials_path: Optional[str] = None
    ):
        """
        Initialize FirestoreUploader.
        
        Args:
            prepared_data_path: Path to prepared data directory
            credentials_path: Path to Firebase credentials JSON
        """
        self.data_path = Path(prepared_data_path)
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self.db: Optional[Any] = None
        
        self.stats = {
            'places_uploaded': 0,
            'cities_uploaded': 0,
            'countries_uploaded': 0,
            'errors': 0
        }
    
    def init_firebase(self) -> Any:
        """Initialize Firebase Admin SDK."""
        if firebase_admin is None:
            raise ImportError(
                "firebase_admin is required for Firestore upload. "
                "Install with: pip install firebase-admin"
            )
        
        try:
            firebase_admin.get_app()
        except ValueError:
            if self.credentials_path and os.path.exists(self.credentials_path):
                cred = credentials.Certificate(self.credentials_path)
                firebase_admin.initialize_app(cred)
            elif os.getenv('FIREBASE_PROJECT_ID'):
                # Use environment variables like main app
                service_account_info = {
                    "type": os.getenv("FIREBASE_TYPE", "service_account"),
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": os.getenv("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
                    "token_uri": os.getenv("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
                    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
                    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
                }
                cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()
        
        self.db = firestore.client()
        return self.db
    
    def transform_place(self, place: Dict) -> Dict:
        """Transform place data for Firestore."""
        doc = {**place}
        
        # Remove id (used as document path)
        doc_id = doc.pop('id', None)
        
        # Convert coordinates to GeoPoint
        coords = doc.get('coordinates')
        if coords and coords.get('latitude') is not None:
            if GeoPoint is not None:
                doc['coordinates'] = GeoPoint(
                    coords['latitude'],
                    coords['longitude']
                )
            else:
                # Fallback: store as dict if GeoPoint not available
                doc['coordinates'] = {
                    'latitude': coords['latitude'],
                    'longitude': coords['longitude']
                }
        else:
            doc['coordinates'] = None
        
        # Add timestamps
        if firestore is not None:
            doc['created_at'] = firestore.SERVER_TIMESTAMP
            doc['updated_at'] = firestore.SERVER_TIMESTAMP
        
        return doc_id, doc
    
    def transform_city(self, city: Dict) -> Dict:
        """Transform city data for Firestore."""
        doc = {**city}
        doc_id = doc.pop('id', None)
        if firestore is not None:
            doc['created_at'] = firestore.SERVER_TIMESTAMP
            doc['updated_at'] = firestore.SERVER_TIMESTAMP
        return doc_id, doc
    
    def transform_country(self, country: Dict) -> Dict:
        """Transform country data for Firestore."""
        doc = {**country}
        doc_id = doc.pop('id', None)
        if firestore is not None:
            doc['created_at'] = firestore.SERVER_TIMESTAMP
            doc['updated_at'] = firestore.SERVER_TIMESTAMP
        return doc_id, doc
    
    def upload_batch(
        self,
        collection_name: str,
        documents: List[Dict],
        transform_fn,
        dry_run: bool = False
    ) -> int:
        """Upload a batch of documents."""
        if dry_run:
            return len(documents)
        
        if not self.db:
            raise RuntimeError("Firebase not initialized")
        
        batch = self.db.batch()
        count = 0
        
        for doc in documents:
            doc_id, doc_data = transform_fn(doc)
            if not doc_id:
                logger.warning("Document missing ID, skipping")
                continue
            
            doc_ref = self.db.collection(collection_name).document(doc_id)
            batch.set(doc_ref, doc_data)
            count += 1
        
        # Commit with retry
        for attempt in range(self.RETRY_COUNT):
            try:
                batch.commit()
                return count
            except Exception as e:
                if attempt == self.RETRY_COUNT - 1:
                    raise
                wait_time = self.RETRY_DELAY * (attempt + 1)
                logger.warning(f"Retry {attempt + 1}/{self.RETRY_COUNT}: Timeout of {wait_time}s exceeded, last exception: {e}")
                time.sleep(wait_time)
        
        return 0
    
    def upload_collection(
        self,
        collection_name: str,
        documents: List[Dict],
        transform_fn,
        dry_run: bool = False
    ) -> Dict:
        """Upload an entire collection."""
        total = len(documents)
        uploaded = 0
        errors = 0
        
        logger.info(f"Uploading {total} documents to '{collection_name}'...")
        
        for i in range(0, total, self.BATCH_SIZE):
            batch_docs = documents[i:i + self.BATCH_SIZE]
            
            try:
                count = self.upload_batch(
                    collection_name,
                    batch_docs,
                    transform_fn,
                    dry_run
                )
                uploaded += count
                
                progress = (uploaded / total) * 100
                logger.info(f"  Progress: {uploaded}/{total} ({progress:.1f}%)")
                
                # Add delay between batches to avoid quota issues
                if not dry_run and i + self.BATCH_SIZE < total:
                    time.sleep(self.BATCH_DELAY)
            
            except Exception as e:
                errors += len(batch_docs)
                logger.error(f"  Batch error: {e}")
        
        return {
            'collection': collection_name,
            'total': total,
            'uploaded': uploaded,
            'errors': errors
        }
    
    def load_data(self) -> Dict[str, List[Dict]]:
        """Load prepared data files."""
        data = {}
        
        places_file = self.data_path / 'places.json'
        if places_file.exists():
            with open(places_file, 'r', encoding='utf-8') as f:
                data['places'] = json.load(f)
            logger.info(f"Loaded {len(data['places'])} places")
        
        cities_file = self.data_path / 'cities.json'
        if cities_file.exists():
            with open(cities_file, 'r', encoding='utf-8') as f:
                data['cities'] = json.load(f)
            logger.info(f"Loaded {len(data['cities'])} cities")
        
        countries_file = self.data_path / 'countries.json'
        if countries_file.exists():
            with open(countries_file, 'r', encoding='utf-8') as f:
                data['countries'] = json.load(f)
            logger.info(f"Loaded {len(data['countries'])} countries")
        
        return data
    
    def run(
        self,
        dry_run: bool = False,
        collections: Optional[List[str]] = None
    ) -> Dict:
        """
        Run the upload process.
        
        Args:
            dry_run: If True, simulate upload without writing
            collections: List of collections to upload (default: all)
        
        Returns:
            Dict with upload results
        """
        if not dry_run:
            self.init_firebase()
        
        data = self.load_data()
        results = {}
        
        upload_all = collections is None
        
        # Upload countries
        if 'countries' in data and (upload_all or 'countries' in collections):
            result = self.upload_collection(
                'countries',
                data['countries'],
                self.transform_country,
                dry_run
            )
            results['countries'] = result
            self.stats['countries_uploaded'] = result['uploaded']
        
        # Upload cities
        if 'cities' in data and (upload_all or 'cities' in collections):
            result = self.upload_collection(
                'cities',
                data['cities'],
                self.transform_city,
                dry_run
            )
            results['cities'] = result
            self.stats['cities_uploaded'] = result['uploaded']
        
        # Upload places
        if 'places' in data and (upload_all or 'places' in collections):
            result = self.upload_collection(
                'places',
                data['places'],
                self.transform_place,
                dry_run
            )
            results['places'] = result
            self.stats['places_uploaded'] = result['uploaded']
        
        return {
            'dry_run': dry_run,
            'results': results,
            'stats': self.stats
        }


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload to Firestore')
    parser.add_argument('--input', default='prepared_data', help='Prepared data directory')
    parser.add_argument('--dry-run', action='store_true', help='Simulate upload')
    parser.add_argument('--collection', help='Specific collection to upload')
    parser.add_argument('--skip', type=int, default=0, help='Skip first N items (for resume)')
    parser.add_argument('--limit', type=int, default=0, help='Limit to N items (0 = all)')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    uploader = FirestoreUploader(prepared_data_path=args.input)
    
    # If resuming with skip/limit, handle specially
    if args.skip > 0 or args.limit > 0:
        if not args.collection:
            print("Error: --skip and --limit require --collection")
            return
        
        uploader.init_firebase()
        data = uploader.load_data()
        
        if args.collection not in data:
            print(f"Error: Collection '{args.collection}' not found")
            return
        
        items = data[args.collection]
        if args.skip > 0:
            items = items[args.skip:]
        if args.limit > 0:
            items = items[:args.limit]
        
        print(f"Uploading {len(items)} items to '{args.collection}' (skip={args.skip}, limit={args.limit})")
        
        transform_fn = {
            'places': uploader.transform_place,
            'cities': uploader.transform_city,
            'countries': uploader.transform_country
        }.get(args.collection)
        
        result = uploader.upload_collection(
            args.collection,
            items,
            transform_fn,
            args.dry_run
        )
        
        print(f"\nUpload complete: {result['uploaded']}/{result['total']}")
        return
    
    collections = [args.collection] if args.collection else None
    results = uploader.run(dry_run=args.dry_run, collections=collections)
    
    print(f"\nUpload {'simulated' if args.dry_run else 'complete'}:")
    for name, result in results.get('results', {}).items():
        print(f"  {name}: {result['uploaded']}/{result['total']}")


if __name__ == '__main__':
    main()
