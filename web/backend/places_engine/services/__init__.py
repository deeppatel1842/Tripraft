"""
Places Engine Services Module

Business logic layer for places operations.
"""

from .places_service import PlacesService
from .intelligent_search import (
    IntelligentSearchService,
    QueryType,
    SearchResult,
    AutocompleteResult,
    QueryNormalizer,
    QueryDetector,
)

__all__ = [
    'PlacesService',
    'IntelligentSearchService',
    'QueryType',
    'SearchResult',
    'AutocompleteResult',
    'QueryNormalizer',
    'QueryDetector',
]
