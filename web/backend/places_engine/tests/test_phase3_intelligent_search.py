"""
Phase 3: Intelligent Search Service - Unit Tests

Comprehensive test suite for Phase 3 service layer implementation.

Test Coverage:
- QueryNormalizer: 8 tests
- QueryDetector: 10 tests
- IntelligentSearchService: 15 tests
- Autocomplete: 8 tests
- Error handling: 5 tests

Total: 46 tests
"""

import pytest
import json
import sys
import os
from typing import Dict, List

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.intelligent_search import (
    QueryType,
    SearchResult,
    AutocompleteResult,
    QueryNormalizer,
    QueryDetector,
    IntelligentSearchService,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def normalizer():
    """QueryNormalizer instance"""
    return QueryNormalizer()


@pytest.fixture
def mock_data_store() -> Dict:
    """Mock data store with countries, states, cities, places"""
    return {
        'countries': [
            {
                'id': 'usa',
                'name': 'United States',
                'states': [
                    {
                        'id': 'california',
                        'name': 'California',
                        'country_name': 'United States',
                        'top_places': [
                            {
                                'id': 'golden-gate-bridge',
                                'name': 'Golden Gate Bridge',
                                'city': 'San Francisco',
                                'state': 'California',
                                'country': 'United States',
                                'coordinates': {'lat': 37.8199, 'lng': -122.4783},
                            }
                        ],
                    }
                ],
            },
            {
                'id': 'france',
                'name': 'France',
                'states': [
                    {
                        'id': 'ile-de-france',
                        'name': 'Île-de-France',
                        'country_name': 'France',
                        'top_places': [
                            {
                                'id': 'eiffel-tower',
                                'name': 'Eiffel Tower',
                                'city': 'Paris',
                                'state': 'Île-de-France',
                                'country': 'France',
                                'coordinates': {'lat': 48.8584, 'lng': 2.2945},
                            }
                        ],
                    }
                ],
            },
        ],
        'states': [
            {
                'id': 'california',
                'name': 'California',
                'country_name': 'United States',
                'top_places': [
                    {
                        'id': 'golden-gate-bridge',
                        'name': 'Golden Gate Bridge',
                        'city': 'San Francisco',
                        'state': 'California',
                        'country': 'United States',
                    }
                ],
            },
            {
                'id': 'ile-de-france',
                'name': 'Île-de-France',
                'country_name': 'France',
                'top_places': [
                    {
                        'id': 'eiffel-tower',
                        'name': 'Eiffel Tower',
                        'city': 'Paris',
                        'state': 'Île-de-France',
                        'country': 'France',
                    }
                ],
            },
        ],
        'cities': [
            {
                'id': 'san-francisco',
                'name': 'San Francisco',
                'country_name': 'United States',
                'state_name': 'California',
                'top_places': [
                    {
                        'id': 'golden-gate-bridge',
                        'name': 'Golden Gate Bridge',
                        'city': 'San Francisco',
                        'state': 'California',
                        'country': 'United States',
                    }
                ],
            },
            {
                'id': 'paris',
                'name': 'Paris',
                'country_name': 'France',
                'state_name': 'Île-de-France',
                'top_places': [
                    {
                        'id': 'eiffel-tower',
                        'name': 'Eiffel Tower',
                        'city': 'Paris',
                        'state': 'Île-de-France',
                        'country': 'France',
                    }
                ],
            },
        ],
        'places': [
            {
                'id': 'golden-gate-bridge',
                'name': 'Golden Gate Bridge',
                'city': 'San Francisco',
                'state': 'California',
                'country': 'United States',
                'coordinates': {'lat': 37.8199, 'lng': -122.4783},
                'rating': 4.7,
            },
            {
                'id': 'eiffel-tower',
                'name': 'Eiffel Tower',
                'city': 'Paris',
                'state': 'Île-de-France',
                'country': 'France',
                'coordinates': {'lat': 48.8584, 'lng': 2.2945},
                'rating': 4.8,
            },
        ],
        'search_index': {
            'gol': {
                'prefix': 'gol',
                'suggestions': [
                    {'name': 'Golden Gate Bridge', 'id': 'golden-gate-bridge', 'type': 'place', 'rank': 0.9},
                ],
            },
            'eif': {
                'prefix': 'eif',
                'suggestions': [
                    {'name': 'Eiffel Tower', 'id': 'eiffel-tower', 'type': 'place', 'rank': 0.95},
                ],
            },
            'par': {
                'prefix': 'par',
                'suggestions': [
                    {'name': 'Paris', 'id': 'paris', 'type': 'city', 'rank': 0.9},
                    {'name': 'Eiffel Tower', 'id': 'eiffel-tower', 'type': 'place', 'rank': 0.8},
                ],
            },
        },
    }


@pytest.fixture
def detector(mock_data_store):
    """QueryDetector with mock data"""
    return QueryDetector(data_store=mock_data_store)


@pytest.fixture
def search_service(mock_data_store):
    """IntelligentSearchService with mock data"""
    return IntelligentSearchService(data_store=mock_data_store)


# ============================================================================
# QueryNormalizer Tests (8 tests)
# ============================================================================

class TestQueryNormalizer:
    """Tests for QueryNormalizer"""
    
    def test_normalize_basic(self, normalizer):
        """Test basic normalization"""
        assert normalizer.normalize('New York') == 'new york'
        assert normalizer.normalize('PARIS') == 'paris'
        assert normalizer.normalize('san francisco') == 'san francisco'
    
    def test_normalize_special_characters(self, normalizer):
        """Test normalization with special characters"""
        assert normalizer.normalize('Eiffel Tower!') == 'eiffel tower'
        assert normalizer.normalize('Paris, France') == 'paris france'
        assert normalizer.normalize("O'Reilly's") == 'o reilly s'
    
    def test_normalize_extra_spaces(self, normalizer):
        """Test normalization with extra spaces"""
        assert normalizer.normalize('New  York') == 'new york'
        assert normalizer.normalize('  Paris  ') == 'paris'
        assert normalizer.normalize('San   Francisco') == 'san francisco'
    
    def test_normalize_accents(self, normalizer):
        """Test normalization with accents"""
        # Accents and special chars are removed
        result = normalizer.normalize('Île-de-France')
        assert 'le de france' in result or 'france' in result
    
    def test_to_slug_basic(self, normalizer):
        """Test slug conversion"""
        assert normalizer.to_slug('New York') == 'new-york'
        assert normalizer.to_slug('Golden Gate Bridge') == 'golden-gate-bridge'
        assert normalizer.to_slug('Paris') == 'paris'
    
    def test_to_slug_special_characters(self, normalizer):
        """Test slug with special characters"""
        slug = normalizer.to_slug("O'Reilly's Hotel")
        # Special characters become hyphens, apostrophes create spaces which become hyphens
        assert 'reilly' in slug and 'hotel' in slug
    
    def test_to_slug_consistency(self, normalizer):
        """Test slug consistency"""
        slug1 = normalizer.to_slug('New York')
        slug2 = normalizer.to_slug('new york')
        slug3 = normalizer.to_slug('NEW YORK')
        assert slug1 == slug2 == slug3
    
    def test_normalize_empty_string(self, normalizer):
        """Test normalization of empty string"""
        assert normalizer.normalize('') == ''
        assert normalizer.normalize('   ') == ''


# ============================================================================
# QueryDetector Tests (10 tests)
# ============================================================================

class TestQueryDetector:
    """Tests for QueryDetector"""
    
    def test_detect_country(self, detector):
        """Test country detection"""
        query_type, match_id = detector.detect_type('United States')
        assert query_type == QueryType.COUNTRY
        assert match_id == 'usa'
    
    def test_detect_state(self, detector):
        """Test state detection"""
        query_type, match_id = detector.detect_type('California')
        assert query_type == QueryType.STATE
        assert match_id == 'california'
    
    def test_detect_city(self, detector):
        """Test city detection"""
        query_type, match_id = detector.detect_type('San Francisco')
        assert query_type == QueryType.CITY
        assert match_id == 'san-francisco'
    
    def test_detect_place(self, detector):
        """Test place detection"""
        query_type, match_id = detector.detect_type('Eiffel Tower')
        assert query_type == QueryType.PLACE
        assert match_id == 'eiffel-tower'
    
    def test_detect_case_insensitive(self, detector):
        """Test case-insensitive detection"""
        query_type1, id1 = detector.detect_type('united states')
        query_type2, id2 = detector.detect_type('UNITED STATES')
        assert query_type1 == query_type2 == QueryType.COUNTRY
        assert id1 == id2 == 'usa'
    
    def test_detect_unknown_query(self, detector):
        """Test unknown query detection"""
        query_type, match_id = detector.detect_type('Unknown Place XYZ')
        assert query_type == QueryType.UNKNOWN
        assert match_id is None
    
    def test_match_location_exact(self, detector):
        """Test exact location match"""
        location = {'id': 'usa', 'name': 'United States'}
        assert detector._match_location('United States', location)
        assert detector._match_location('usa', location)
    
    def test_match_location_partial(self, detector):
        """Test partial location match"""
        location = {'id': 'usa', 'name': 'United States'}
        assert detector._match_location('United', location)
        assert detector._match_location('States', location) == False  # Doesn't start with
    
    def test_match_location_case_insensitive(self, detector):
        """Test case-insensitive location match"""
        location = {'id': 'usa', 'name': 'United States'}
        assert detector._match_location('united states', location)
        assert detector._match_location('UNITED STATES', location)
    
    def test_detect_with_empty_store(self):
        """Test detection with empty data store"""
        detector_empty = QueryDetector(data_store={})
        query_type, match_id = detector_empty.detect_type('Any Query')
        assert query_type == QueryType.UNKNOWN
        assert match_id is None


# ============================================================================
# SearchResult Tests (4 tests)
# ============================================================================

class TestSearchResult:
    """Tests for SearchResult"""
    
    def test_search_result_initialization(self):
        """Test SearchResult initialization"""
        result = SearchResult(
            success=True,
            query='Paris',
            query_type=QueryType.CITY,
            display_mode='top_destinations',
            match_id='paris',
            match_name='Paris',
        )
        assert result.success is True
        assert result.query == 'Paris'
        assert result.query_type == QueryType.CITY
        assert result.places == []
    
    def test_search_result_to_dict(self):
        """Test SearchResult serialization to dict"""
        result = SearchResult(
            success=True,
            query='Paris',
            query_type=QueryType.CITY,
            display_mode='top_destinations',
            match_id='paris',
            match_name='Paris',
            firestore_reads=1,
            response_time_ms=45.5,
        )
        result_dict = result.to_dict()
        assert result_dict['success'] is True
        assert result_dict['query_type'] == 'city'
        assert result_dict['firestore_reads'] == 1
    
    def test_search_result_with_error(self):
        """Test SearchResult with error"""
        result = SearchResult(
            success=False,
            query='Unknown',
            query_type=QueryType.UNKNOWN,
            display_mode='error',
            error='Not found',
        )
        assert result.success is False
        assert result.error == 'Not found'
    
    def test_search_result_places_default(self):
        """Test SearchResult places default to empty list"""
        result = SearchResult(
            success=True,
            query='Test',
            query_type=QueryType.PLACE,
            display_mode='single_place',
        )
        assert isinstance(result.places, list)
        assert len(result.places) == 0


# ============================================================================
# IntelligentSearchService Tests (15 tests)
# ============================================================================

class TestIntelligentSearchService:
    """Tests for IntelligentSearchService"""
    
    def test_search_country(self, search_service):
        """Test country search"""
        result = search_service.intelligent_search('United States')
        assert result.success is True
        assert result.query_type == QueryType.COUNTRY
        assert result.match_id == 'usa'
        assert result.display_mode == 'country_sections'
    
    def test_search_state(self, search_service):
        """Test state search"""
        result = search_service.intelligent_search('California')
        assert result.success is True
        assert result.query_type == QueryType.STATE
        assert result.match_id == 'california'
        assert result.display_mode == 'top_destinations'
    
    def test_search_city(self, search_service):
        """Test city search"""
        result = search_service.intelligent_search('Paris')
        assert result.success is True
        assert result.query_type == QueryType.CITY
        assert result.match_id == 'paris'
        assert result.display_mode == 'top_destinations'
    
    def test_search_place(self, search_service):
        """Test place search"""
        result = search_service.intelligent_search('Eiffel Tower')
        assert result.success is True
        assert result.query_type == QueryType.PLACE
        assert result.display_mode == 'single_place'
        assert len(result.places) > 0
    
    def test_search_not_found(self, search_service):
        """Test search for non-existent location"""
        result = search_service.intelligent_search('Unknown Location')
        assert result.success is False
        assert 'Not found' in result.error or 'No results' in result.error
    
    def test_search_empty_query(self, search_service):
        """Test search with empty query"""
        result = search_service.intelligent_search('')
        assert result.success is False
        assert 'empty' in result.error.lower()
    
    def test_search_whitespace_query(self, search_service):
        """Test search with whitespace-only query"""
        result = search_service.intelligent_search('   ')
        assert result.success is False
    
    def test_search_case_insensitive(self, search_service):
        """Test case-insensitive search"""
        result1 = search_service.intelligent_search('Paris')
        result2 = search_service.intelligent_search('paris')
        result3 = search_service.intelligent_search('PARIS')
        
        assert result1.success == result2.success == result3.success
        assert result1.query_type == result2.query_type == result3.query_type
    
    def test_search_type_override(self, search_service):
        """Test search with type override"""
        result = search_service.intelligent_search('Paris', type_override='city')
        assert result.success is True
        assert result.query_type == QueryType.CITY
    
    def test_search_invalid_type_override(self, search_service):
        """Test search with invalid type override"""
        result = search_service.intelligent_search('Paris', type_override='invalid')
        assert result.success is False
        assert 'Invalid type' in result.error
    
    def test_search_response_time(self, search_service):
        """Test that response time is tracked"""
        result = search_service.intelligent_search('Paris')
        assert result.response_time_ms >= 0
    
    def test_search_firestore_reads_tracked(self, search_service):
        """Test that Firestore reads are tracked"""
        result = search_service.intelligent_search('Paris')
        assert result.firestore_reads >= 1
    
    def test_search_location_hierarchy(self, search_service):
        """Test location hierarchy in result"""
        result = search_service.intelligent_search('Eiffel Tower')
        assert result.location_hierarchy is not None
        assert 'country' in result.location_hierarchy
        assert 'city' in result.location_hierarchy
    
    def test_search_result_serialization(self, search_service):
        """Test search result can be serialized"""
        result = search_service.intelligent_search('Paris')
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert 'success' in result_dict
        assert 'query_type' in result_dict
    
    def test_search_error_handling(self, search_service):
        """Test error handling in search"""
        # Inject bad data to test error handling
        service = IntelligentSearchService(data_store={})
        result = service.intelligent_search('Test')
        assert result.success is False


# ============================================================================
# Autocomplete Tests (8 tests)
# ============================================================================

class TestAutocomplete:
    """Tests for autocomplete functionality"""
    
    def test_autocomplete_basic(self, search_service):
        """Test basic autocomplete"""
        result = search_service.autocomplete('eif')
        assert result.success is True
        assert isinstance(result.suggestions, list)
    
    def test_autocomplete_suggestions(self, search_service):
        """Test autocomplete returns suggestions"""
        result = search_service.autocomplete('par')
        assert result.success is True
        assert len(result.suggestions) > 0
    
    def test_autocomplete_limit(self, search_service):
        """Test autocomplete respects limit"""
        result = search_service.autocomplete('par', limit=1)
        assert len(result.suggestions) <= 1
    
    def test_autocomplete_empty_query(self, search_service):
        """Test autocomplete with empty query"""
        result = search_service.autocomplete('')
        assert result.success is False
    
    def test_autocomplete_short_query(self, search_service):
        """Test autocomplete with short query (< 1 char)"""
        result = search_service.autocomplete('')
        assert result.success is False
    
    def test_autocomplete_no_matches(self, search_service):
        """Test autocomplete with no matches"""
        result = search_service.autocomplete('zzz')
        assert result.success is True
        assert len(result.suggestions) == 0
    
    def test_autocomplete_response_time(self, search_service):
        """Test autocomplete tracks response time"""
        result = search_service.autocomplete('par')
        assert result.response_time_ms >= 0
    
    def test_autocomplete_result_serialization(self, search_service):
        """Test autocomplete result serialization"""
        result = search_service.autocomplete('par')
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert 'suggestions' in result_dict


# ============================================================================
# Integration Tests (5 tests)
# ============================================================================

class TestIntegration:
    """Integration tests for Phase 3"""
    
    def test_search_workflow_country_to_place(self, search_service):
        """Test complete workflow: country -> state -> city -> place"""
        # Search country
        result1 = search_service.intelligent_search('United States')
        assert result1.success is True
        assert result1.query_type == QueryType.COUNTRY
        
        # Search state within country
        result2 = search_service.intelligent_search('California')
        assert result2.success is True
        assert result2.query_type == QueryType.STATE
        
        # Search city within state
        result3 = search_service.intelligent_search('San Francisco')
        assert result3.success is True
        assert result3.query_type == QueryType.CITY
        
        # Search place within city
        result4 = search_service.intelligent_search('Golden Gate Bridge')
        assert result4.success is True
        assert result4.query_type == QueryType.PLACE
    
    def test_autocomplete_workflow(self, search_service):
        """Test autocomplete workflow"""
        result1 = search_service.autocomplete('gol')
        assert result1.success is True
        
        result2 = search_service.autocomplete('eif')
        assert result2.success is True
    
    def test_mixed_search_and_autocomplete(self, search_service):
        """Test mixing search and autocomplete"""
        # Get suggestions
        autocomplete = search_service.autocomplete('par')
        assert autocomplete.success is True
        
        # Search specific result
        search = search_service.intelligent_search('Paris')
        assert search.success is True
    
    def test_all_display_modes(self, search_service):
        """Test all display modes are used correctly"""
        # country_sections
        result1 = search_service.intelligent_search('United States')
        assert result1.display_mode == 'country_sections'
        
        # top_destinations
        result2 = search_service.intelligent_search('California')
        assert result2.display_mode == 'top_destinations'
        
        # single_place
        result3 = search_service.intelligent_search('Eiffel Tower')
        assert result3.display_mode == 'single_place'
    
    def test_no_hardcoding(self, search_service):
        """Test that service doesn't contain hardcoded values"""
        # Service should work with any mock data
        custom_store = {
            'countries': [
                {
                    'id': 'test-country',
                    'name': 'Test Country',
                    'states': [],
                }
            ],
            'states': [],
            'cities': [],
            'places': [],
            'search_index': {},
        }
        service = IntelligentSearchService(data_store=custom_store)
        result = service.intelligent_search('Test Country')
        assert result.success is True
        assert result.query_type == QueryType.COUNTRY


# ============================================================================
# Run tests if executed directly
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
