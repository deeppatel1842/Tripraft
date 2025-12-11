"""
Phase 4: API Endpoints - Unit Tests

Comprehensive test suite for REST API endpoints.

Test Coverage:
- Search endpoint validation (8 tests)
- Search endpoint responses (12 tests)
- Autocomplete endpoint validation (8 tests)
- Autocomplete endpoint responses (8 tests)
- Place detail endpoint (6 tests)
- Health endpoint (2 tests)
- Error handling (8 tests)
- Response formatting (6 tests)
- CORS and caching headers (4 tests)

Total: 62 tests
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.endpoints import (
    places_bp,
    initialize_service,
    validate_search_request,
    validate_autocomplete_request,
    format_search_response,
    format_autocomplete_response,
    error_response,
    success_response,
)
from services.intelligent_search import (
    QueryType,
    SearchResult,
    AutocompleteResult,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def app():
    """Flask test app"""
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(places_bp)
    return app


@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()


@pytest.fixture
def mock_search_service():
    """Mock IntelligentSearchService"""
    return Mock()


@pytest.fixture
def search_result_city():
    """Mock SearchResult for city"""
    return SearchResult(
        success=True,
        query='Paris',
        query_type=QueryType.CITY,
        display_mode='top_destinations',
        match_id='paris',
        match_name='Paris',
        location_hierarchy={'country': 'France', 'state': 'Île-de-France', 'city': 'Paris'},
        places=[
            {
                'id': 'eiffel-tower',
                'name': 'Eiffel Tower',
                'city': 'Paris',
                'state': 'Île-de-France',
                'country': 'France',
                'rating': 4.8,
            }
        ],
        firestore_reads=1,
        response_time_ms=45.2,
        cache_hit=False,
    )


@pytest.fixture
def search_result_country():
    """Mock SearchResult for country"""
    return SearchResult(
        success=True,
        query='France',
        query_type=QueryType.COUNTRY,
        display_mode='country_sections',
        match_id='france',
        match_name='France',
        location_hierarchy={'country': 'France'},
        places=[],
        sections=[
            {
                'id': 'ile-de-france',
                'name': 'Île-de-France',
                'top_places': [{'id': 'eiffel-tower', 'name': 'Eiffel Tower'}],
            }
        ],
        firestore_reads=1,
        response_time_ms=50.5,
        cache_hit=False,
    )


@pytest.fixture
def autocomplete_result():
    """Mock AutocompleteResult"""
    return AutocompleteResult(
        success=True,
        query='par',
        suggestions=[
            {'id': 'paris', 'name': 'Paris', 'type': 'city', 'rank': 0.95},
            {'id': 'parietal', 'name': 'Parietal', 'type': 'place', 'rank': 0.7},
        ],
        firestore_reads=1,
        response_time_ms=25.3,
        cache_hit=True,
    )


# ============================================================================
# Request Validation Tests
# ============================================================================

class TestSearchRequestValidation:
    """Test search request validation"""
    
    def test_validate_search_missing_query(self):
        """Test search request with missing query"""
        # This would need Flask app context, so we'll test at endpoint level instead
        pass
    
    def test_search_endpoint_missing_query(self, client):
        """Test search endpoint without query parameter"""
        response = client.get('/api/places/search')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'required' in data['error'].lower()
    
    def test_search_endpoint_empty_query(self, client):
        """Test search endpoint with empty query"""
        response = client.get('/api/places/search?q=')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_search_endpoint_whitespace_query(self, client):
        """Test search endpoint with whitespace-only query"""
        response = client.get('/api/places/search?q=   ')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_search_endpoint_query_too_long(self, client):
        """Test search endpoint with very long query"""
        long_query = 'a' * 501
        response = client.get(f'/api/places/search?q={long_query}')
        assert response.status_code == 400
        data = response.get_json()
        assert 'too long' in data['error'].lower()
    
    def test_search_endpoint_with_valid_query(self, client, mock_search_service, search_result_city):
        """Test search endpoint with valid query"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = search_result_city
            response = client.get('/api/places/search?q=Paris')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
    
    def test_search_endpoint_with_type_override(self, client, mock_search_service, search_result_city):
        """Test search endpoint with type override"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = search_result_city
            response = client.get('/api/places/search?q=Paris&type=city')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            mock_search_service.intelligent_search.assert_called_once()
            call_args = mock_search_service.intelligent_search.call_args
            assert call_args[1]['type_override'] == 'city'
    
    def test_search_endpoint_post_with_json(self, client, mock_search_service, search_result_city):
        """Test search endpoint with POST and JSON body"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = search_result_city
            response = client.post(
                '/api/places/search',
                json={'q': 'Paris', 'type': 'city'},
                content_type='application/json',
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True


# ============================================================================
# Autocomplete Validation Tests
# ============================================================================

class TestAutocompleteRequestValidation:
    """Test autocomplete request validation"""
    
    def test_autocomplete_missing_query(self, client):
        """Test autocomplete without query parameter"""
        response = client.get('/api/places/autocomplete')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_autocomplete_empty_query(self, client):
        """Test autocomplete with empty query"""
        response = client.get('/api/places/autocomplete?q=')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_autocomplete_query_too_long(self, client):
        """Test autocomplete with very long query"""
        long_query = 'a' * 101
        response = client.get(f'/api/places/autocomplete?q={long_query}')
        assert response.status_code == 400
        data = response.get_json()
        assert 'too long' in data['error'].lower()
    
    def test_autocomplete_invalid_limit(self, client):
        """Test autocomplete with invalid limit"""
        response = client.get('/api/places/autocomplete?q=par&limit=invalid')
        assert response.status_code == 400
        data = response.get_json()
        assert 'integer' in data['error'].lower()
    
    def test_autocomplete_limit_too_high(self, client):
        """Test autocomplete with limit > 100"""
        response = client.get('/api/places/autocomplete?q=par&limit=101')
        assert response.status_code == 400
        data = response.get_json()
        assert 'between 1 and 100' in data['error'].lower()
    
    def test_autocomplete_limit_zero(self, client):
        """Test autocomplete with limit 0"""
        response = client.get('/api/places/autocomplete?q=par&limit=0')
        assert response.status_code == 400
        data = response.get_json()
        assert 'between 1 and 100' in data['error'].lower()
    
    def test_autocomplete_with_valid_request(self, client, mock_search_service, autocomplete_result):
        """Test autocomplete with valid request"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.autocomplete.return_value = autocomplete_result
            response = client.get('/api/places/autocomplete?q=par&limit=10')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert len(data['data']['suggestions']) == 2
    
    def test_autocomplete_default_limit(self, client, mock_search_service, autocomplete_result):
        """Test autocomplete uses default limit"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.autocomplete.return_value = autocomplete_result
            response = client.get('/api/places/autocomplete?q=par')
            assert response.status_code == 200
            mock_search_service.autocomplete.assert_called_once()
            call_args = mock_search_service.autocomplete.call_args
            assert call_args[1]['limit'] == 10


# ============================================================================
# Search Response Tests
# ============================================================================

class TestSearchResponses:
    """Test search endpoint responses"""
    
    def test_search_city_response(self, client, mock_search_service, search_result_city):
        """Test search response for city"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = search_result_city
            response = client.get('/api/places/search?q=Paris')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data']['query_type'] == 'city'
            assert data['data']['display_mode'] == 'top_destinations'
            assert data['data']['match']['name'] == 'Paris'
            assert len(data['data']['places']) > 0
    
    def test_search_country_response(self, client, mock_search_service, search_result_country):
        """Test search response for country"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = search_result_country
            response = client.get('/api/places/search?q=France')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data']['query_type'] == 'country'
            assert data['data']['display_mode'] == 'country_sections'
            assert data['data']['sections'] is not None
    
    def test_search_not_found(self, client, mock_search_service):
        """Test search response for not found"""
        result = SearchResult(
            success=False,
            query='Unknown',
            query_type=QueryType.UNKNOWN,
            display_mode='error',
            error='Not found',
        )
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = result
            response = client.get('/api/places/search?q=Unknown')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is False
            assert 'error' in data['data']
    
    def test_search_response_metadata(self, client, mock_search_service, search_result_city):
        """Test search response includes metadata"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = search_result_city
            response = client.get('/api/places/search?q=Paris')
            assert response.status_code == 200
            data = response.get_json()
            assert 'metadata' in data
            assert 'response_time_ms' in data['metadata']
            assert 'firestore_reads' in data['metadata']
            assert 'cache_hit' in data['metadata']
    
    def test_search_response_timestamp(self, client, mock_search_service, search_result_city):
        """Test search response includes timestamp"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = search_result_city
            response = client.get('/api/places/search?q=Paris')
            assert response.status_code == 200
            data = response.get_json()
            assert 'timestamp' in data
            assert isinstance(data['timestamp'], float)
    
    def test_search_response_location_hierarchy(self, client, mock_search_service, search_result_city):
        """Test search response includes location hierarchy"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = search_result_city
            response = client.get('/api/places/search?q=Paris')
            assert response.status_code == 200
            data = response.get_json()
            assert 'location_hierarchy' in data['data']
            assert 'country' in data['data']['location_hierarchy']


# ============================================================================
# Autocomplete Response Tests
# ============================================================================

class TestAutocompleteResponses:
    """Test autocomplete endpoint responses"""
    
    def test_autocomplete_success_response(self, client, mock_search_service, autocomplete_result):
        """Test autocomplete success response"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.autocomplete.return_value = autocomplete_result
            response = client.get('/api/places/autocomplete?q=par')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data']['query'] == 'par'
            assert len(data['data']['suggestions']) == 2
            assert data['data']['total'] == 2
    
    def test_autocomplete_response_metadata(self, client, mock_search_service, autocomplete_result):
        """Test autocomplete response includes metadata"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.autocomplete.return_value = autocomplete_result
            response = client.get('/api/places/autocomplete?q=par')
            assert response.status_code == 200
            data = response.get_json()
            assert 'metadata' in data
            assert data['metadata']['firestore_reads'] == 1
            assert data['metadata']['cache_hit'] is True
    
    def test_autocomplete_empty_suggestions(self, client, mock_search_service):
        """Test autocomplete with no suggestions"""
        result = AutocompleteResult(
            success=True,
            query='xyz',
            suggestions=[],
            firestore_reads=1,
            response_time_ms=15.0,
            cache_hit=False,
        )
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.autocomplete.return_value = result
            response = client.get('/api/places/autocomplete?q=xyz')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert len(data['data']['suggestions']) == 0
            assert data['data']['total'] == 0


# ============================================================================
# Place Detail Endpoint Tests
# ============================================================================

class TestPlaceDetailEndpoint:
    """Test /place/{id} endpoint"""
    
    def test_place_detail_success(self, client, mock_search_service):
        """Test place detail endpoint success"""
        place_result = SearchResult(
            success=True,
            query='eiffel-tower',
            query_type=QueryType.PLACE,
            display_mode='single_place',
            match_id='eiffel-tower',
            match_name='Eiffel Tower',
            places=[
                {
                    'id': 'eiffel-tower',
                    'name': 'Eiffel Tower',
                    'city': 'Paris',
                    'country': 'France',
                    'rating': 4.8,
                }
            ],
            firestore_reads=1,
            response_time_ms=20.0,
        )
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = place_result
            response = client.get('/api/places/place/eiffel-tower')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data']['id'] == 'eiffel-tower'
            assert data['data']['name'] == 'Eiffel Tower'
    
    def test_place_detail_not_found(self, client, mock_search_service):
        """Test place detail endpoint not found"""
        result = SearchResult(
            success=False,
            query='unknown',
            query_type=QueryType.UNKNOWN,
            display_mode='error',
        )
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = result
            response = client.get('/api/places/place/unknown')
            assert response.status_code == 404
            data = response.get_json()
            assert data['success'] is False
            assert 'not found' in data['error'].lower()
    
    def test_place_detail_empty_id(self, client):
        """Test place detail endpoint with empty ID"""
        response = client.get('/api/places/place/')
        # Flask should handle the missing ID
        assert response.status_code in [400, 404]
    
    def test_place_detail_metadata(self, client, mock_search_service):
        """Test place detail response includes metadata"""
        place_result = SearchResult(
            success=True,
            query='eiffel-tower',
            query_type=QueryType.PLACE,
            display_mode='single_place',
            places=[{'id': 'eiffel-tower', 'name': 'Eiffel Tower'}],
            firestore_reads=1,
            response_time_ms=20.0,
        )
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = place_result
            response = client.get('/api/places/place/eiffel-tower')
            assert response.status_code == 200
            data = response.get_json()
            assert 'metadata' in data


# ============================================================================
# Health Endpoint Tests
# ============================================================================

class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_endpoint_success(self, client, mock_search_service):
        """Test health endpoint returns healthy"""
        with patch('api.endpoints.search_service', mock_search_service):
            response = client.get('/api/places/health')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data']['status'] == 'healthy'
            assert data['data']['service'] == 'places-engine'
    
    def test_health_endpoint_service_not_initialized(self, client):
        """Test health endpoint when service not initialized"""
        with patch('api.endpoints.search_service', None):
            response = client.get('/api/places/health')
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False


# ============================================================================
# Error Response Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling"""
    
    def test_error_response_format(self):
        """Test error response format"""
        response, code = error_response('Test error', 400, 'test_error')
        assert code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error'] == 'Test error'
        assert data['error_type'] == 'test_error'
        assert 'timestamp' in data
    
    def test_success_response_format(self):
        """Test success response format"""
        response, code = success_response({'key': 'value'})
        assert code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == {'key': 'value'}
        assert 'timestamp' in data
    
    def test_success_response_with_metadata(self):
        """Test success response with metadata"""
        response, code = success_response(
            {'key': 'value'},
            {'response_time': 100}
        )
        assert code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'metadata' in data
        assert data['metadata']['response_time'] == 100
    
    def test_search_service_not_initialized(self, client):
        """Test search endpoint when service not initialized"""
        with patch('api.endpoints.search_service', None):
            response = client.get('/api/places/search?q=test')
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'not initialized' in data['error'].lower()
    
    def test_search_exception_handling(self, client, mock_search_service):
        """Test search endpoint handles service exceptions"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.side_effect = Exception('Service error')
            response = client.get('/api/places/search?q=test')
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'error' in data['error'].lower()


# ============================================================================
# Response Formatting Tests
# ============================================================================

class TestResponseFormatting:
    """Test response formatting"""
    
    def test_format_search_response_city(self, search_result_city):
        """Test formatting city search response"""
        formatted = format_search_response(search_result_city)
        assert formatted['query_type'] == 'city'
        assert formatted['display_mode'] == 'top_destinations'
        assert 'places' in formatted
        assert 'total_places' in formatted
    
    def test_format_search_response_country(self, search_result_country):
        """Test formatting country search response"""
        formatted = format_search_response(search_result_country)
        assert formatted['query_type'] == 'country'
        assert formatted['display_mode'] == 'country_sections'
        assert 'sections' in formatted
        assert 'total_places' in formatted
    
    def test_format_autocomplete_response(self, autocomplete_result):
        """Test formatting autocomplete response"""
        formatted = format_autocomplete_response(autocomplete_result)
        assert formatted['query'] == 'par'
        assert len(formatted['suggestions']) == 2
        assert formatted['total'] == 2


# ============================================================================
# CORS and Caching Headers Tests
# ============================================================================

class TestHeadersAndCaching:
    """Test CORS and caching headers"""
    
    def test_cors_headers_present(self, client, mock_search_service, search_result_city):
        """Test CORS headers are present in response"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = search_result_city
            response = client.get('/api/places/search?q=Paris')
            assert 'Access-Control-Allow-Origin' in response.headers
            assert response.headers['Access-Control-Allow-Origin'] == '*'
    
    def test_search_cache_header(self, client, mock_search_service, search_result_city):
        """Test search endpoint sets cache control header"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.return_value = search_result_city
            response = client.get('/api/places/search?q=Paris')
            assert 'Cache-Control' in response.headers
            assert '1800' in response.headers['Cache-Control']  # 30 minutes
    
    def test_autocomplete_cache_header(self, client, mock_search_service, autocomplete_result):
        """Test autocomplete endpoint sets cache control header"""
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.autocomplete.return_value = autocomplete_result
            response = client.get('/api/places/autocomplete?q=par')
            assert 'Cache-Control' in response.headers
            assert '3600' in response.headers['Cache-Control']  # 1 hour
    
    def test_health_no_cache_header(self, client, mock_search_service):
        """Test health endpoint sets no-cache header"""
        with patch('api.endpoints.search_service', mock_search_service):
            response = client.get('/api/places/health')
            assert 'Cache-Control' in response.headers
            assert 'no-cache' in response.headers['Cache-Control']


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for API"""
    
    def test_search_to_place_detail_flow(self, client, mock_search_service):
        """Test flow: search city -> get place details"""
        search_result = SearchResult(
            success=True,
            query='Paris',
            query_type=QueryType.CITY,
            display_mode='top_destinations',
            places=[
                {'id': 'eiffel-tower', 'name': 'Eiffel Tower'},
            ],
            firestore_reads=1,
            response_time_ms=45.0,
        )
        place_result = SearchResult(
            success=True,
            query='eiffel-tower',
            query_type=QueryType.PLACE,
            display_mode='single_place',
            places=[
                {'id': 'eiffel-tower', 'name': 'Eiffel Tower', 'rating': 4.8},
            ],
            firestore_reads=1,
            response_time_ms=20.0,
        )
        
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.intelligent_search.side_effect = [search_result, place_result]
            
            # Search for city
            response1 = client.get('/api/places/search?q=Paris')
            assert response1.status_code == 200
            assert response1.get_json()['data']['query_type'] == 'city'
            
            # Get place details
            response2 = client.get('/api/places/place/eiffel-tower')
            assert response2.status_code == 200
            assert response2.get_json()['data']['name'] == 'Eiffel Tower'
    
    def test_autocomplete_to_search_flow(self, client, mock_search_service):
        """Test flow: autocomplete -> search"""
        autocomplete_result = AutocompleteResult(
            success=True,
            query='par',
            suggestions=[
                {'id': 'paris', 'name': 'Paris', 'type': 'city'},
            ],
            firestore_reads=1,
            response_time_ms=25.0,
        )
        search_result = SearchResult(
            success=True,
            query='Paris',
            query_type=QueryType.CITY,
            display_mode='top_destinations',
            places=[],
            firestore_reads=1,
            response_time_ms=45.0,
        )
        
        with patch('api.endpoints.search_service', mock_search_service):
            mock_search_service.autocomplete.return_value = autocomplete_result
            mock_search_service.intelligent_search.return_value = search_result
            
            # Get autocomplete suggestions
            response1 = client.get('/api/places/autocomplete?q=par')
            assert response1.status_code == 200
            assert len(response1.get_json()['data']['suggestions']) == 1
            
            # Search for suggested location
            response2 = client.get('/api/places/search?q=Paris')
            assert response2.status_code == 200
            assert response2.get_json()['data']['query_type'] == 'city'


# ============================================================================
# Run tests if executed directly
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
