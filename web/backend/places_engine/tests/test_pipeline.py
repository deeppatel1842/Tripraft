"""
Tests for places_engine.pipeline module.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestDatasetAnalyzer:
    """Test DatasetAnalyzer class."""
    
    def test_import_analyzer(self):
        """Test analyzer can be imported."""
        from places_engine.pipeline import DatasetAnalyzer
        assert DatasetAnalyzer is not None
    
    def test_create_analyzer(self):
        """Test analyzer can be created."""
        from places_engine.pipeline import DatasetAnalyzer
        analyzer = DatasetAnalyzer()
        assert analyzer is not None


class TestPhotoValidator:
    """Test PhotoValidator class."""
    
    def test_import_validator(self):
        """Test validator can be imported."""
        from places_engine.pipeline import PhotoValidator
        assert PhotoValidator is not None
    
    def test_create_validator(self):
        """Test validator can be created."""
        from places_engine.pipeline import PhotoValidator
        validator = PhotoValidator()
        assert validator is not None
    
    def test_is_invalid_url_commons_logo(self):
        """Test commons-logo.svg is detected as invalid."""
        from places_engine.pipeline import PhotoValidator
        validator = PhotoValidator()
        is_invalid, reason = validator.is_invalid_url('https://example.com/Commons-logo.svg')
        assert is_invalid is True
        assert reason is not None
    
    def test_is_invalid_url_flag(self):
        """Test flag_of_ pattern is detected as invalid."""
        from places_engine.pipeline import PhotoValidator
        validator = PhotoValidator()
        is_invalid, reason = validator.is_invalid_url('https://example.com/Flag_of_Argentina.svg')
        assert is_invalid is True
    
    def test_is_valid_url_jpg(self):
        """Test valid JPG photo is accepted."""
        from places_engine.pipeline import PhotoValidator
        validator = PhotoValidator()
        is_invalid, reason = validator.is_invalid_url('https://example.com/place_photo.jpg')
        # Should return False (not invalid) for valid photos
        assert is_invalid is False


class TestDatasetPreparer:
    """Test DatasetPreparer class."""
    
    def test_import_preparer(self):
        """Test preparer can be imported."""
        from places_engine.pipeline import DatasetPreparer
        assert DatasetPreparer is not None
    
    def test_normalize_text(self):
        """Test text normalization."""
        from places_engine.pipeline import DatasetPreparer
        preparer = DatasetPreparer()
        assert preparer.normalize_text('Hello World') == 'hello world'
        assert preparer.normalize_text('  Multiple   Spaces  ') == 'multiple spaces'
    
    def test_normalize_id(self):
        """Test ID normalization."""
        from places_engine.pipeline import DatasetPreparer
        preparer = DatasetPreparer()
        assert preparer.normalize_id('New York City') == 'new_york_city'
        assert preparer.normalize_id('São Paulo') == 'so_paulo' or 's_o_paulo' in preparer.normalize_id('São Paulo')
    
    def test_generate_place_id(self):
        """Test place ID generation."""
        from places_engine.pipeline import DatasetPreparer
        preparer = DatasetPreparer()
        place_id = preparer.generate_place_id('Argentina', 'Buenos Aires', 'Obelisco')
        assert 'argentina' in place_id
        assert 'buenos' in place_id or 'buenos_aires' in place_id
        assert 'obelisco' in place_id
    
    def test_is_valid_photo_url(self):
        """Test photo URL validation."""
        from places_engine.pipeline import DatasetPreparer
        preparer = DatasetPreparer()
        
        # Valid URLs
        assert preparer.is_valid_photo_url('https://example.com/photo.jpg') is True
        
        # Invalid URLs (placeholders)
        assert preparer.is_valid_photo_url('https://example.com/commons-logo.svg') is False
        assert preparer.is_valid_photo_url(None) is False
        assert preparer.is_valid_photo_url('') is False
    
    def test_sanitize_photos_empty(self):
        """Test sanitize_photos with empty input."""
        from places_engine.pipeline import DatasetPreparer
        preparer = DatasetPreparer()
        result = preparer.sanitize_photos(None)
        assert result['has_valid_photo'] is False
        assert result['thumbnail_url'] is None
    
    def test_generate_search_text(self):
        """Test search text generation."""
        from places_engine.pipeline import DatasetPreparer
        preparer = DatasetPreparer()
        place = {
            'name': 'Eiffel Tower',
            'city': 'Paris',
            'country': 'France',
            'tags': ['Landmark', 'Architecture']
        }
        search_text = preparer.generate_search_text(place)
        assert 'eiffel tower' in search_text
        assert 'paris' in search_text
        assert 'france' in search_text
        assert 'landmark' in search_text


class TestFirestoreUploader:
    """Test FirestoreUploader class."""
    
    def test_import_uploader(self):
        """Test uploader can be imported."""
        from places_engine.pipeline import FirestoreUploader
        assert FirestoreUploader is not None
    
    def test_create_uploader(self):
        """Test uploader can be created."""
        from places_engine.pipeline import FirestoreUploader
        uploader = FirestoreUploader()
        assert uploader is not None
    
    def test_batch_size_limit(self):
        """Test batch size is within Firestore limit."""
        from places_engine.pipeline import FirestoreUploader
        uploader = FirestoreUploader()
        assert uploader.BATCH_SIZE <= 500
    
    def test_transform_place_basic(self):
        """Test basic place transformation."""
        from places_engine.pipeline import FirestoreUploader
        uploader = FirestoreUploader()
        
        place = {
            'id': 'test_place',
            'name': 'Test Place',
            'coordinates': {'latitude': 40.7, 'longitude': -74.0}
        }
        
        doc_id, doc = uploader.transform_place(place)
        assert doc_id == 'test_place'
        assert 'id' not in doc  # ID should be removed from doc
        assert doc['name'] == 'Test Place'
    
    def test_transform_place_null_coordinates(self):
        """Test place transformation with null coordinates."""
        from places_engine.pipeline import FirestoreUploader
        uploader = FirestoreUploader()
        
        place = {
            'id': 'test_place',
            'name': 'Test Place',
            'coordinates': None
        }
        
        doc_id, doc = uploader.transform_place(place)
        assert doc['coordinates'] is None
