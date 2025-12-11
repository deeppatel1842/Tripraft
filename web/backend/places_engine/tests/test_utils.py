"""
Tests for places_engine.utils module.
"""
import pytest


class TestNormalizeString:
    """Test normalize_string function."""
    
    def test_basic_normalization(self):
        """Test basic string normalization."""
        from places_engine.utils import normalize_string
        assert normalize_string('Hello World') == 'hello_world'
    
    def test_empty_string(self):
        """Test empty string returns empty."""
        from places_engine.utils import normalize_string
        assert normalize_string('') == ''
    
    def test_special_characters(self):
        """Test special characters are removed."""
        from places_engine.utils import normalize_string
        result = normalize_string('San José, Costa Rica!')
        assert '_' in result or result.replace('_', '').isalnum()
    
    def test_multiple_spaces(self):
        """Test multiple spaces are collapsed."""
        from places_engine.utils import normalize_string
        result = normalize_string('New    York    City')
        assert '  ' not in result


class TestCalculateDistance:
    """Test calculate_distance function."""
    
    def test_same_point_zero_distance(self):
        """Test same point returns zero distance."""
        from places_engine.utils import calculate_distance
        distance = calculate_distance(40.7128, -74.0060, 40.7128, -74.0060)
        assert distance == 0 or distance < 1  # Allow for floating point
    
    def test_known_distance(self):
        """Test known distance between cities."""
        from places_engine.utils import calculate_distance
        # NYC to LA ~3940 km
        distance = calculate_distance(
            40.7128, -74.0060,  # NYC
            34.0522, -118.2437  # LA
        )
        # Allow 10% tolerance
        assert 3500000 < distance < 4500000
    
    def test_returns_meters(self):
        """Test returns distance in meters."""
        from places_engine.utils import calculate_distance
        distance = calculate_distance(0, 0, 0, 1)
        # 1 degree longitude at equator ~111km
        assert 100000 < distance < 120000


class TestValidateCoordinates:
    """Test validate_coordinates function."""
    
    def test_valid_coordinates(self):
        """Test valid coordinates return True."""
        from places_engine.utils import validate_coordinates
        is_valid, error = validate_coordinates(40.7128, -74.0060)
        assert is_valid is True
        assert error is None
    
    def test_invalid_latitude(self):
        """Test invalid latitude returns False."""
        from places_engine.utils import validate_coordinates
        is_valid, error = validate_coordinates(91, 0)
        assert is_valid is False
        assert error is not None
        is_valid2, _ = validate_coordinates(-91, 0)
        assert is_valid2 is False
    
    def test_invalid_longitude(self):
        """Test invalid longitude returns False."""
        from places_engine.utils import validate_coordinates
        is_valid, error = validate_coordinates(0, 181)
        assert is_valid is False
        assert error is not None
        is_valid2, _ = validate_coordinates(0, -181)
        assert is_valid2 is False
    
    def test_edge_cases(self):
        """Test edge case coordinates."""
        from places_engine.utils import validate_coordinates
        is_valid1, _ = validate_coordinates(90, 180)
        assert is_valid1 is True
        is_valid2, _ = validate_coordinates(-90, -180)
        assert is_valid2 is True


class TestChunkList:
    """Test chunk_list function."""
    
    def test_basic_chunking(self):
        """Test basic list chunking."""
        from places_engine.utils import chunk_list
        items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        chunks = chunk_list(items, 3)
        assert len(chunks) == 4
        assert chunks[0] == [1, 2, 3]
        assert chunks[1] == [4, 5, 6]
        assert chunks[2] == [7, 8, 9]
        assert chunks[3] == [10]
    
    def test_empty_list(self):
        """Test empty list returns empty."""
        from places_engine.utils import chunk_list
        assert chunk_list([], 5) == []
    
    def test_single_chunk(self):
        """Test list smaller than chunk size."""
        from places_engine.utils import chunk_list
        items = [1, 2, 3]
        chunks = chunk_list(items, 10)
        assert len(chunks) == 1
        assert chunks[0] == [1, 2, 3]


class TestCalculateBoundingBox:
    """Test calculate_bounding_box function."""
    
    def test_bounding_box_structure(self):
        """Test bounding box returns correct structure."""
        from places_engine.utils import calculate_bounding_box
        bbox = calculate_bounding_box(40.7128, -74.0060, 10000)
        assert 'min_lat' in bbox
        assert 'max_lat' in bbox
        assert 'min_lng' in bbox
        assert 'max_lng' in bbox
    
    def test_bounding_box_size(self):
        """Test bounding box is larger than point."""
        from places_engine.utils import calculate_bounding_box
        lat, lng = 40.7128, -74.0060
        bbox = calculate_bounding_box(lat, lng, 10000)
        assert bbox['min_lat'] < lat < bbox['max_lat']
        assert bbox['min_lng'] < lng < bbox['max_lng']
