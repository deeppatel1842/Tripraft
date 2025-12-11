"""
Pytest configuration for Phase 21 Extreme Services tests.

Sets up Firebase and other mocks before any imports.
"""

import sys
from unittest.mock import MagicMock, patch

# Create comprehensive firebase mocks BEFORE any imports
firebase_admin_mock = MagicMock()
firebase_admin_mock.get_app.return_value = MagicMock()
firebase_admin_mock.initialize_app.return_value = MagicMock()

firestore_mock = MagicMock()
firestore_mock.client.return_value = MagicMock()
firestore_mock.SERVER_TIMESTAMP = 'SERVER_TIMESTAMP'
firestore_mock.Increment = MagicMock(side_effect=lambda x: x)
firestore_mock.DELETE_FIELD = 'DELETE_FIELD'
firestore_mock.ArrayUnion = MagicMock(side_effect=lambda x: x)
firestore_mock.ArrayRemove = MagicMock(side_effect=lambda x: x)

# Mock google cloud firestore
gcloud_firestore_mock = MagicMock()
gcloud_firestore_mock.__version__ = '2.0.0'
gcloud_firestore_mock.SERVER_TIMESTAMP = 'SERVER_TIMESTAMP'
gcloud_firestore_mock.Increment = MagicMock(side_effect=lambda x: x)

# Mock all firebase related modules
sys.modules['firebase_admin'] = firebase_admin_mock
sys.modules['firebase_admin.firestore'] = firestore_mock
sys.modules['firebase_admin.auth'] = MagicMock()
sys.modules['firebase_admin.credentials'] = MagicMock()
sys.modules['google.cloud.firestore'] = gcloud_firestore_mock
sys.modules['google.cloud.firestore_v1'] = MagicMock()
sys.modules['google.cloud.firestore_v1.base_query'] = MagicMock()
sys.modules['google.cloud.firestore_v1.base_collection'] = MagicMock()
