"""
Tests for places_engine.config module.
"""
import pytest
from pathlib import Path


class TestPlacesEngineConfig:
    """Test PlacesEngineConfig class."""
    
    def test_import_config(self):
        """Test config can be imported."""
        from places_engine.config import PlacesEngineConfig
        assert PlacesEngineConfig is not None
    
    def test_config_singleton(self):
        """Test get_config returns singleton."""
        from places_engine.config import get_config
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
    
    def test_dataset_path_is_path(self):
        """Test dataset_path returns Path object."""
        from places_engine.config import PlacesEngineConfig
        config = PlacesEngineConfig()
        assert isinstance(config.dataset_path, Path)
    
    def test_output_path_is_path(self):
        """Test output_path returns Path object."""
        from places_engine.config import PlacesEngineConfig
        config = PlacesEngineConfig()
        assert isinstance(config.output_path, Path)
    
    def test_collection_names(self):
        """Test collection names are strings."""
        from places_engine.config import PlacesEngineConfig
        config = PlacesEngineConfig()
        assert config.COLLECTION_PLACES == 'places'
        assert config.COLLECTION_CITIES == 'cities'
        assert config.COLLECTION_COUNTRIES == 'countries'
    
    def test_batch_size_positive(self):
        """Test batch size is positive."""
        from places_engine.config import PlacesEngineConfig
        config = PlacesEngineConfig()
        assert config.FIRESTORE_BATCH_SIZE > 0
        assert config.FIRESTORE_BATCH_SIZE <= 500  # Firestore limit
    
    def test_cache_ttls_positive(self):
        """Test cache TTLs are positive."""
        from places_engine.config import PlacesEngineConfig
        config = PlacesEngineConfig()
        assert config.CACHE_TTL_LOCATION_SEARCH > 0
        assert config.CACHE_TTL_COUNTRY_OVERVIEW > 0
        assert config.CACHE_TTL_NEARBY_SEARCH > 0
    
    def test_invalid_photo_patterns_exist(self):
        """Test invalid photo patterns are defined."""
        from places_engine.config import PlacesEngineConfig
        config = PlacesEngineConfig()
        assert len(config.INVALID_PHOTO_PATTERNS) > 0
        assert 'commons-logo.svg' in config.INVALID_PHOTO_PATTERNS
    
    def test_place_defaults_exist(self):
        """Test place defaults are defined."""
        from places_engine.config import PlacesEngineConfig
        config = PlacesEngineConfig()
        assert 'rank_score' in config.PLACE_DEFAULTS
        assert 'cost' in config.PLACE_DEFAULTS
        assert config.PLACE_DEFAULTS['rank_score'] >= 0
        assert config.PLACE_DEFAULTS['rank_score'] <= 1
    
    def test_api_limits(self):
        """Test API limits are reasonable."""
        from places_engine.config import PlacesEngineConfig
        config = PlacesEngineConfig()
        assert config.API_DEFAULT_LIMIT == 20
        assert config.API_MAX_LIMIT >= config.API_DEFAULT_LIMIT
    
    def test_place_schema_defined(self):
        """Test place schema is defined."""
        from places_engine.config import PlacesEngineConfig
        config = PlacesEngineConfig()
        schema = config.PLACE_SCHEMA
        assert 'id' in schema
        assert 'name' in schema
        assert 'city' in schema
        assert 'country' in schema
        assert 'rank_score' in schema
        assert 'coordinates' in schema


class TestBackwardsCompatibility:
    """Test backwards compatibility exports."""
    
    def test_module_level_constants(self):
        """Test module-level constants are exported."""
        from places_engine.config import (
            COLLECTION_PLACES,
            COLLECTION_CITIES,
            COLLECTION_COUNTRIES,
            FIRESTORE_BATCH_SIZE,
            API_DEFAULT_LIMIT,
        )
        assert COLLECTION_PLACES == 'places'
        assert isinstance(FIRESTORE_BATCH_SIZE, int)
        assert isinstance(API_DEFAULT_LIMIT, int)
