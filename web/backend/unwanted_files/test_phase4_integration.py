"""
Phase 4: API Integration Tests

Tests for Phase 4 helper functions and integration with Phase 3.

Test Coverage:
- Response formatting (10 tests)
- Error responses (8 tests)
- Success responses (6 tests)
- Request validation (12 tests)
- Integration tests (6 tests)

Total: 42 tests
"""

import pytest
import time
from unittest.mock import Mock
import sys
import os

# Add parent directories to path  
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly without going through api/__init__.py
from api.phase4_helpers import (
    create_success_response,
    create_error_response,
    validate_query_parameter,
    validate_limit_parameter,
    format_search_result,
    format_autocomplete_result,
    create_search_response,
    create_autocomplete_response,
    missing_service_error,
    server_error,
)
from services.intelligent_search import (
    QueryType,
    SearchResult,
    AutocompleteResult,
)


# ============================================================================
# Response Helper Tests
# ============================================================================

class TestSuccessResponse:
    """Test success response creation"""
    
    def test_success_response_basic(self):
        """Test basic success response"""
        data = {'key': 'value'}
        response, code = create_success_response(data)
        
        assert code == 200
        assert response['success'] is True
        assert response['data'] == data
        assert 'timestamp' in response
    
    def test_success_response_with_metadata(self):
        """Test success response with metadata"""
        data = {'key': 'value'}
        metadata = {'response_time_ms': 45.2, 'reads': 1}
        response, code = create_success_response(data, metadata)
        
        assert code == 200
        assert response['success'] is True
        assert response['metadata'] == metadata
    
    def test_success_response_without_metadata(self):
        """Test success response without metadata"""
        data = {'key': 'value'}
        response, code = create_success_response(data)
        
        assert 'metadata' not in response
    
    def test_success_response_empty_data(self):
        """Test success response with empty data"""
        response, code = create_success_response({})
        assert code == 200
        assert response['data'] == {}
    
    def test_success_response_list_data(self):
        """Test success response with list data"""
        data = [1, 2, 3]
        response, code = create_success_response(data)
        assert response['data'] == data
    
    def test_success_response_timestamp_type(self):
        """Test success response timestamp is float"""
        response, code = create_success_response({})
        assert isinstance(response['timestamp'], float)


class TestErrorResponse:
    """Test error response creation"""
    
    def test_error_response_basic(self):
        """Test basic error response"""
        response, code = create_error_response('Test error', 400)
        
        assert code == 400
        assert response['success'] is False
        assert response['error'] == 'Test error'
        assert response['error_type'] == 'error'
        assert 'timestamp' in response
    
    def test_error_response_custom_type(self):
        """Test error response with custom type"""
        response, code = create_error_response(
            'Not found',
            404,
            'not_found'
        )
        
        assert code == 404
        assert response['error_type'] == 'not_found'
    
    def test_error_response_various_codes(self):
        """Test error response with various status codes"""
        for http_code in [400, 401, 403, 404, 500, 503]:
            response, code = create_error_response('Error', http_code)
            assert code == http_code
    
    def test_error_response_empty_message(self):
        """Test error response with empty message"""
        response, code = create_error_response('', 400)
        assert response['error'] == ''
    
    def test_error_response_long_message(self):
        """Test error response with long message"""
        long_message = 'x' * 1000
        response, code = create_error_response(long_message, 400)
        assert response['error'] == long_message


# ============================================================================
# Request Validation Tests
# ============================================================================

class TestQueryValidation:
    """Test query parameter validation"""
    
    def test_validate_query_valid(self):
        """Test validation with valid query"""
        query, error = validate_query_parameter('Paris')
        assert query == 'Paris'
        assert error is None
    
    def test_validate_query_missing(self):
        """Test validation with missing query"""
        query, error = validate_query_parameter(None)
        assert query is None
        assert error is not None
        assert error[1] == 400
        assert 'required' in error[0]['error'].lower()
    
    def test_validate_query_empty_string(self):
        """Test validation with empty string"""
        query, error = validate_query_parameter('')
        assert query is None
        assert error is not None
    
    def test_validate_query_whitespace_only(self):
        """Test validation with whitespace only"""
        query, error = validate_query_parameter('   ')
        assert query is None
        assert error is not None
    
    def test_validate_query_too_long(self):
        """Test validation with query too long"""
        long_query = 'a' * 501
        query, error = validate_query_parameter(long_query)
        assert query is None
        assert error is not None
        assert 'too long' in error[0]['error'].lower()
    
    def test_validate_query_custom_limits(self):
        """Test validation with custom limits"""
        query, error = validate_query_parameter(
            'ab',
            min_length=3,
            max_length=100
        )
        assert query is None
        assert error is not None
    
    def test_validate_query_strips_whitespace(self):
        """Test validation strips whitespace"""
        query, error = validate_query_parameter('  Paris  ')
        assert query == 'Paris'
        assert error is None


class TestLimitValidation:
    """Test limit parameter validation"""
    
    def test_validate_limit_valid(self):
        """Test validation with valid limit"""
        limit, error = validate_limit_parameter('10')
        assert limit == 10
        assert error is None
    
    def test_validate_limit_default(self):
        """Test validation with no limit provided"""
        limit, error = validate_limit_parameter(None)
        assert limit == 10  # default
        assert error is None
    
    def test_validate_limit_empty_string(self):
        """Test validation with empty string"""
        limit, error = validate_limit_parameter('')
        assert limit == 10  # default
        assert error is None
    
    def test_validate_limit_invalid_not_integer(self):
        """Test validation with non-integer"""
        limit, error = validate_limit_parameter('abc')
        assert limit is None
        assert error is not None
        assert 'integer' in error[0]['error'].lower()
    
    def test_validate_limit_too_high(self):
        """Test validation with limit too high"""
        limit, error = validate_limit_parameter('101')
        assert limit is None
        assert error is not None
        assert 'between' in error[0]['error'].lower()
    
    def test_validate_limit_zero(self):
        """Test validation with limit 0"""
        limit, error = validate_limit_parameter('0')
        assert limit is None
        assert error is not None
    
    def test_validate_limit_negative(self):
        """Test validation with negative limit"""
        limit, error = validate_limit_parameter('-5')
        assert limit is None
        assert error is not None
    
    def test_validate_limit_custom_range(self):
        """Test validation with custom range"""
        limit, error = validate_limit_parameter('5', min_value=1, max_value=50)
        assert limit == 5
        assert error is None


# ============================================================================
# Response Formatting Tests
# ============================================================================

class TestSearchResultFormatting:
    """Test search result formatting"""
    
    def test_format_search_result_city_success(self):
        """Test formatting successful city search"""
        result = SearchResult(
            success=True,
            query='Paris',
            query_type=QueryType.CITY,
            display_mode='top_destinations',
            match_id='paris',
            match_name='Paris',
            location_hierarchy={'country': 'France', 'city': 'Paris'},
            places=[{'id': 'eiffel', 'name': 'Eiffel Tower'}],
            firestore_reads=1,
        )
        
        formatted = format_search_result(result)
        assert 'success' not in formatted  # Not included for success
        assert formatted['query'] == 'Paris'
        assert formatted['query_type'] == 'city'
        assert formatted['display_mode'] == 'top_destinations'
        assert len(formatted['places']) == 1
        assert formatted['total_places'] == 1
    
    def test_format_search_result_country_success(self):
        """Test formatting successful country search"""
        result = SearchResult(
            success=True,
            query='France',
            query_type=QueryType.COUNTRY,
            display_mode='country_sections',
            sections=[{'id': 'ile', 'name': 'Île-de-France'}],
            places=[],
            firestore_reads=1,
        )
        
        formatted = format_search_result(result)
        assert formatted['query_type'] == 'country'
        assert formatted['display_mode'] == 'country_sections'
        assert 'sections' in formatted
        assert formatted['total_places'] == 0
    
    def test_format_search_result_place_success(self):
        """Test formatting successful place search"""
        place = {'id': 'eiffel', 'name': 'Eiffel Tower'}
        result = SearchResult(
            success=True,
            query='Eiffel Tower',
            query_type=QueryType.PLACE,
            display_mode='single_place',
            places=[place],
            firestore_reads=1,
        )
        
        formatted = format_search_result(result)
        assert formatted['query_type'] == 'place'
        assert formatted['display_mode'] == 'single_place'
        assert formatted['place'] == place
    
    def test_format_search_result_failure(self):
        """Test formatting failed search"""
        result = SearchResult(
            success=False,
            query='Unknown',
            query_type=QueryType.UNKNOWN,
            display_mode='error',
            error='Not found',
        )
        
        formatted = format_search_result(result)
        assert formatted['success'] is False
        assert 'error' in formatted
    
    def test_format_search_result_match_info(self):
        """Test formatting includes match info"""
        result = SearchResult(
            success=True,
            query='Paris',
            query_type=QueryType.CITY,
            display_mode='top_destinations',
            match_id='paris',
            match_name='Paris',
            places=[],
            firestore_reads=1,
        )
        
        formatted = format_search_result(result)
        assert formatted['match']['id'] == 'paris'
        assert formatted['match']['name'] == 'Paris'
    
    def test_format_search_result_no_match(self):
        """Test formatting without match"""
        result = SearchResult(
            success=True,
            query='Test',
            query_type=QueryType.UNKNOWN,
            display_mode='error',
            places=[],
            firestore_reads=1,
        )
        
        formatted = format_search_result(result)
        assert formatted['match'] is None


class TestAutocompleteResultFormatting:
    """Test autocomplete result formatting"""
    
    def test_format_autocomplete_result_success(self):
        """Test formatting successful autocomplete"""
        suggestions = [
            {'id': 'paris', 'name': 'Paris', 'type': 'city'},
            {'id': 'parietal', 'name': 'Parietal', 'type': 'place'},
        ]
        result = AutocompleteResult(
            success=True,
            query='par',
            suggestions=suggestions,
            firestore_reads=1,
        )
        
        formatted = format_autocomplete_result(result)
        assert formatted['query'] == 'par'
        assert len(formatted['suggestions']) == 2
        assert formatted['total'] == 2
    
    def test_format_autocomplete_result_empty(self):
        """Test formatting autocomplete with no suggestions"""
        result = AutocompleteResult(
            success=True,
            query='xyz',
            suggestions=[],
            firestore_reads=1,
        )
        
        formatted = format_autocomplete_result(result)
        assert len(formatted['suggestions']) == 0
        assert formatted['total'] == 0
    
    def test_format_autocomplete_result_failure(self):
        """Test formatting failed autocomplete"""
        result = AutocompleteResult(
            success=False,
            query='test',
            suggestions=[],
            error='Service error',
        )
        
        formatted = format_autocomplete_result(result)
        assert 'error' in formatted
        assert formatted['suggestions'] == []
        assert formatted['total'] == 0


# ============================================================================
# Endpoint Response Tests
# ============================================================================

class TestSearchResponse:
    """Test search endpoint response creation"""
    
    def test_search_response_success(self):
        """Test successful search response"""
        result = SearchResult(
            success=True,
            query='Paris',
            query_type=QueryType.CITY,
            display_mode='top_destinations',
            places=[],
            firestore_reads=1,
            response_time_ms=45.2,
        )
        
        response, code = create_search_response(result, 50.0)
        assert code == 200
        assert response['success'] is True
        assert 'metadata' in response
        assert response['metadata']['firestore_reads'] == 1


class TestAutocompleteResponse:
    """Test autocomplete endpoint response creation"""
    
    def test_autocomplete_response_success(self):
        """Test successful autocomplete response"""
        result = AutocompleteResult(
            success=True,
            query='par',
            suggestions=[{'id': 'paris', 'name': 'Paris'}],
            firestore_reads=1,
        )
        
        response, code = create_autocomplete_response(result, 25.0)
        assert code == 200
        assert response['success'] is True
        assert 'metadata' in response


# ============================================================================
# Error Response Wrappers
# ============================================================================

class TestErrorWrappers:
    """Test error response wrappers"""
    
    def test_missing_service_error(self):
        """Test missing service error"""
        response, code = missing_service_error()
        assert code == 503
        assert response['success'] is False
        assert 'service' in response['error'].lower()
    
    def test_server_error(self):
        """Test server error wrapper"""
        exception = Exception('Test error')
        response, code = server_error(exception)
        assert code == 500
        assert response['success'] is False


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests"""
    
    def test_full_search_flow(self):
        """Test full search flow"""
        # Create a search result
        result = SearchResult(
            success=True,
            query='Paris',
            query_type=QueryType.CITY,
            display_mode='top_destinations',
            match_id='paris',
            match_name='Paris',
            places=[{'id': 'eiffel', 'name': 'Eiffel Tower'}],
            firestore_reads=1,
            response_time_ms=45.0,
        )
        
        # Create response
        response, code = create_search_response(result, 50.0)
        
        # Verify
        assert code == 200
        assert response['success'] is True
        assert response['data']['query'] == 'Paris'
        assert response['metadata']['response_time_ms'] == 50.0
    
    def test_full_autocomplete_flow(self):
        """Test full autocomplete flow"""
        # Create autocomplete result
        result = AutocompleteResult(
            success=True,
            query='par',
            suggestions=[
                {'id': 'paris', 'name': 'Paris', 'type': 'city'},
            ],
            firestore_reads=1,
            response_time_ms=25.0,
        )
        
        # Create response
        response, code = create_autocomplete_response(result, 30.0)
        
        # Verify
        assert code == 200
        assert response['success'] is True
        assert response['data']['total'] == 1


# ============================================================================
# Run tests if executed directly
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
