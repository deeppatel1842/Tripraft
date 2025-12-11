#!/usr/bin/env python3
"""
Quick script to check total document count in each Firestore collection.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file
env_paths = [
    os.path.join(os.path.dirname(__file__), '../../.env'),
    os.path.join(os.path.dirname(__file__), '../../../.env'),
    '.env'
]
env_file = next((p for p in env_paths if os.path.exists(p)), None)
if env_file:
    load_dotenv(env_file)

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    print("ERROR: firebase-admin SDK not found. Install with: pip install firebase-admin")
    sys.exit(1)

# Build credentials dict from environment
cred_dict = {
    'type': os.getenv('FIREBASE_TYPE'),
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

cred = credentials.Certificate(cred_dict)
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    pass

db = firestore.client()

print("\n" + "="*80)
print("FIRESTORE COLLECTION DOCUMENT COUNT")
print("="*80)

collections = ['countries', 'states', 'cities', 'search_index']
total_docs = 0

for collection_name in collections:
    # Use aggregation query to get accurate count
    try:
        count_query = db.collection(collection_name).count()
        doc_count = count_query.get()[0][0].value
        print(f"\n{collection_name}: {doc_count:,} documents")
        total_docs += doc_count
        
        # Get first document to verify structure
        docs = db.collection(collection_name).limit(1).get()
        if docs:
            first_doc = docs[0]
            print(f"  Sample doc ID: {first_doc.id}")
            print(f"  Fields: {list(first_doc.to_dict().keys())}")
    except Exception as e:
        print(f"\n{collection_name}: ERROR - {str(e)}")

print(f"\n{'-'*80}")
print(f"TOTAL DOCUMENTS: {total_docs:,}")
print("="*80)
