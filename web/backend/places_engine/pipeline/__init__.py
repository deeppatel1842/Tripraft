"""
Places Engine Pipeline Module

Data processing pipeline for places data:
- Dataset analysis
- Photo validation
- Data preparation
- Firestore upload
- Full automation pipeline
"""

from .analyze_dataset import DatasetAnalyzer
from .validate_photos import PhotoValidator
from .prepare_dataset import DatasetPreparer
from .upload_to_firestore import FirestoreUploader
from .run_full_pipeline import FullPipeline
from .aggregate_top_places import DataAggregator
from .generate_search_index import SearchIndexGenerator

__all__ = [
    'DatasetAnalyzer',
    'PhotoValidator',
    'DatasetPreparer',
    'FirestoreUploader',
    'FullPipeline',
    'DataAggregator',
    'SearchIndexGenerator',
]
