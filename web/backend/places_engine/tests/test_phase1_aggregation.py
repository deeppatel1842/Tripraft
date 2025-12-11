"""
Unit Tests for Phase 1: Data Aggregation

Tests for:
- Data model creation and conversion
- City aggregation
- State aggregation
- Country aggregation
- Data persistence
- Search text generation
"""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from places_engine.models import (
    Place, City, State, Country, Coordinates, PlacePhoto, PlaceOpeningHours, StateTopPlaces
)
from places_engine.pipeline.aggregate_top_places import DataAggregator


class TestPlaceDataModels(unittest.TestCase):
    """Test Place data model creation and conversion"""
    
    def test_place_creation_minimal(self):
        """Test creating a Place with minimal fields"""
        place = Place(
            id="test_place_1",
            name="Test Place",
            city="Test City",
            state="Test State",
            country="Test Country"
        )
        
        self.assertEqual(place.id, "test_place_1")
        self.assertEqual(place.name, "Test Place")
        self.assertEqual(place.city, "Test City")
        self.assertEqual(place.rank_score, 0.6)  # Default
    
    def test_place_creation_full(self):
        """Test creating a Place with all fields"""
        place = Place(
            id="test_place_2",
            name="Cerro Catedral Ski Resort",
            city="Bariloche",
            state="Bariloche",
            country="Argentina",
            ai_summary="Largest ski resort...",
            rating_tourist_priority=5.0,
            rating_traveler_experience=5.0,
            rank_score=0.92,
            cost="Paid (Lift tickets/activity passes)",
            suggested_duration="Half-day to Full-day",
            best_time_to_visit="Jun–Oct (Skiing); Dec–Mar (Summer activities)",
            place_tip="Book ski passes in advance...",
            tags=["Ski Resort", "Skiing", "Snowboarding"],
            coordinates=Coordinates(latitude=-41.1683, longitude=-71.4397),
        )
        
        self.assertEqual(place.rank_score, 0.92)
        self.assertEqual(place.cost, "Paid (Lift tickets/activity passes)")
        self.assertEqual(len(place.tags), 3)
        self.assertEqual(place.coordinates.latitude, -41.1683)
    
    def test_place_to_dict(self):
        """Test Place.to_dict() conversion"""
        place = Place(
            id="test_1",
            name="Test Place",
            city="Test City",
            state="Test State",
            country="Test Country",
            coordinates=Coordinates(latitude=10.0, longitude=20.0),
            tags=["tag1", "tag2"],
        )
        
        place_dict = place.to_dict()
        
        self.assertIsInstance(place_dict, dict)
        self.assertEqual(place_dict['id'], "test_1")
        self.assertEqual(place_dict['name'], "Test Place")
        self.assertIn('coordinates', place_dict)
        self.assertEqual(place_dict['coordinates']['latitude'], 10.0)
        self.assertEqual(place_dict['coordinates']['longitude'], 20.0)
    
    def test_coordinates_creation(self):
        """Test Coordinates dataclass"""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)
        
        self.assertEqual(coords.latitude, 40.7128)
        self.assertEqual(coords.longitude, -74.0060)
    
    def test_opening_hours_creation(self):
        """Test PlaceOpeningHours dataclass"""
        hours = PlaceOpeningHours(
            monday="9:00 AM - 5:00 PM",
            tuesday="9:00 AM - 5:00 PM",
            wednesday="9:00 AM - 5:00 PM",
            notes="Closed on holidays"
        )
        
        self.assertEqual(hours.monday, "9:00 AM - 5:00 PM")
        self.assertEqual(hours.notes, "Closed on holidays")
    
    def test_city_creation(self):
        """Test City dataclass"""
        places = [
            Place(id="p1", name="Place 1", city="NYC", state="NY", country="USA", rank_score=0.95),
            Place(id="p2", name="Place 2", city="NYC", state="NY", country="USA", rank_score=0.85),
        ]
        
        city = City(
            id="nyc",
            name="New York City",
            state="New York",
            country="USA",
            place_count=2,
            top_places=places,
        )
        
        self.assertEqual(city.id, "nyc")
        self.assertEqual(city.name, "New York City")
        self.assertEqual(len(city.top_places), 2)
        self.assertEqual(city.place_count, 2)
    
    def test_state_creation(self):
        """Test State dataclass"""
        places = [
            Place(id="p1", name="Place 1", city="NYC", state="NY", country="USA"),
            Place(id="p2", name="Place 2", city="Boston", state="MA", country="USA"),
        ]
        
        state = State(
            id="ny",
            name="New York",
            country="USA",
            place_count=2,
            cities=[
                {"city_id": "nyc", "city_name": "NYC", "place_count": 1}
            ],
            top_places=places,
        )
        
        self.assertEqual(state.id, "ny")
        self.assertEqual(len(state.top_places), 2)
        self.assertEqual(state.city_count, 1)
    
    def test_country_creation(self):
        """Test Country dataclass"""
        place1 = Place(id="p1", name="Place 1", city="NYC", state="NY", country="USA", rank_score=0.95)
        place2 = Place(id="p2", name="Place 2", city="LA", state="CA", country="USA", rank_score=0.90)
        
        state_ny = StateTopPlaces(
            state_id="ny",
            state_name="New York",
            place_count=1,
            top_places=[place1]
        )
        
        state_ca = StateTopPlaces(
            state_id="ca",
            state_name="California",
            place_count=1,
            top_places=[place2]
        )
        
        country = Country(
            id="usa",
            name="United States",
            state_count=2,
            place_count=2,
            states=[state_ny, state_ca]
        )
        
        self.assertEqual(country.id, "usa")
        self.assertEqual(country.state_count, 2)
        self.assertEqual(len(country.states), 2)


class TestDataAggregator(unittest.TestCase):
    """Test DataAggregator functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create prepared_data directory with sample data
        self.prepared_data_path = self.temp_path / 'prepared_data'
        self.prepared_data_path.mkdir()
        
        # Create sample places.json
        self.sample_places = [
            {
                "id": "usa_ny_statue_of_liberty",
                "name": "Statue of Liberty",
                "name_normalized": "statue_of_liberty",
                "city": "New York",
                "city_normalized": "new_york",
                "state": "New York",
                "state_normalized": "new_york",
                "country": "United States",
                "country_normalized": "united_states",
                "ai_summary": "Iconic statue symbolizing freedom...",
                "rank_score": 0.98,
                "coordinates": {"latitude": 40.6892, "longitude": -74.0445},
                "rating_tourist_priority": 5,
                "rating_traveler_experience": 5,
                "tags": ["monument", "historical"],
            },
            {
                "id": "usa_ny_central_park",
                "name": "Central Park",
                "name_normalized": "central_park",
                "city": "New York",
                "city_normalized": "new_york",
                "state": "New York",
                "state_normalized": "new_york",
                "country": "United States",
                "country_normalized": "united_states",
                "ai_summary": "Large urban park...",
                "rank_score": 0.95,
                "coordinates": {"latitude": 40.7829, "longitude": -73.9654},
                "rating_tourist_priority": 5,
                "rating_traveler_experience": 4.8,
                "tags": ["park", "nature"],
            },
            {
                "id": "usa_ca_golden_gate",
                "name": "Golden Gate Bridge",
                "name_normalized": "golden_gate_bridge",
                "city": "San Francisco",
                "city_normalized": "san_francisco",
                "state": "California",
                "state_normalized": "california",
                "country": "United States",
                "country_normalized": "united_states",
                "ai_summary": "Iconic suspension bridge...",
                "rank_score": 0.96,
                "coordinates": {"latitude": 37.8199, "longitude": -122.4783},
                "rating_tourist_priority": 5,
                "rating_traveler_experience": 4.9,
                "tags": ["bridge", "architecture"],
            },
        ]
        
        places_file = self.prepared_data_path / 'places.json'
        with open(places_file, 'w') as f:
            json.dump(self.sample_places, f)
        
        self.aggregator = DataAggregator(str(self.prepared_data_path))
    
    def tearDown(self):
        """Clean up temporary directory"""
        self.temp_dir.cleanup()
    
    def test_load_prepared_data(self):
        """Test loading prepared data"""
        success = self.aggregator.load_prepared_data()
        
        self.assertTrue(success)
        self.assertEqual(self.aggregator.stats['places_read'], 3)
        self.assertEqual(len(self.aggregator.places), 3)
        self.assertEqual(len(self.aggregator.places_by_city), 2)  # NYC and SF
    
    def test_aggregate_cities(self):
        """Test city aggregation"""
        self.aggregator.load_prepared_data()
        cities = self.aggregator.aggregate_cities()
        
        self.assertGreater(len(cities), 0)
        
        # Find NYC
        nyc = next((c for c in cities if c.name == "New York"), None)
        self.assertIsNotNone(nyc)
        self.assertEqual(nyc.place_count, 2)
        self.assertEqual(len(nyc.top_places), 2)
        self.assertEqual(nyc.top_places[0].rank_score, 0.98)  # Highest ranked first
    
    def test_aggregate_states(self):
        """Test state aggregation"""
        self.aggregator.load_prepared_data()
        states = self.aggregator.aggregate_states()
        
        self.assertGreater(len(states), 0)
        
        # Find New York state
        ny_state = next((s for s in states if s.name == "New York"), None)
        self.assertIsNotNone(ny_state)
        self.assertEqual(ny_state.place_count, 2)
        self.assertGreater(ny_state.city_count, 0)
    
    def test_aggregate_countries(self):
        """Test country aggregation"""
        self.aggregator.load_prepared_data()
        countries = self.aggregator.aggregate_countries()
        
        self.assertGreater(len(countries), 0)
        
        # Find USA
        usa = next((c for c in countries if c.name == "United States"), None)
        self.assertIsNotNone(usa)
        self.assertEqual(usa.place_count, 3)
        self.assertGreater(usa.state_count, 0)
    
    def test_get_top_places(self):
        """Test getting top N places by rank_score"""
        self.aggregator.load_prepared_data()
        
        all_places = self.aggregator.places
        top_2 = self.aggregator._get_top_places(all_places, 2)
        
        self.assertEqual(len(top_2), 2)
        self.assertEqual(top_2[0].rank_score, 0.98)  # Statue of Liberty
        self.assertEqual(top_2[1].rank_score, 0.96)  # Golden Gate
    
    def test_generate_search_text(self):
        """Test search text generation"""
        self.aggregator.load_prepared_data()
        cities = self.aggregator.aggregate_cities()
        
        nyc = next((c for c in cities if c.name == "New York"), None)
        self.assertIsNotNone(nyc)
        self.assertIsNotNone(nyc.search_text)
        self.assertIn("new york", nyc.search_text)
        self.assertIn("monument", nyc.search_text)
    
    def test_save_aggregated_data(self):
        """Test saving aggregated data"""
        self.aggregator.load_prepared_data()
        
        cities = self.aggregator.aggregate_cities()
        states = self.aggregator.aggregate_states()
        countries = self.aggregator.aggregate_countries()
        
        success = self.aggregator.save_aggregated_data(cities, states, countries)
        
        self.assertTrue(success)
        
        # Verify files were created
        self.assertTrue((self.aggregator.output_path / 'cities_aggregated.json').exists())
        self.assertTrue((self.aggregator.output_path / 'states_aggregated.json').exists())
        self.assertTrue((self.aggregator.output_path / 'countries_aggregated.json').exists())
        self.assertTrue((self.aggregator.output_path / 'aggregation_stats.json').exists())
    
    def test_full_run(self):
        """Test full aggregation pipeline"""
        success = self.aggregator.run()
        
        self.assertTrue(success)
        self.assertEqual(self.aggregator.stats['errors'], 0)
        self.assertGreater(self.aggregator.stats['cities_created'], 0)
        self.assertGreater(self.aggregator.stats['states_created'], 0)
        self.assertGreater(self.aggregator.stats['countries_created'], 0)


class TestDataConsistency(unittest.TestCase):
    """Test data consistency across all aggregation levels"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create prepared_data directory
        self.prepared_data_path = self.temp_path / 'prepared_data'
        self.prepared_data_path.mkdir()
        
        # Create comprehensive sample data
        self.sample_places = []
        
        # Add 30 places to NYC
        for i in range(30):
            self.sample_places.append({
                "id": f"usa_ny_place_{i}",
                "name": f"New York Place {i}",
                "city": "New York",
                "state": "New York",
                "country": "United States",
                "rank_score": 1.0 - (i * 0.01),  # Descending scores
                "coordinates": {"latitude": 40.7128 + i * 0.001, "longitude": -74.0060},
            })
        
        places_file = self.prepared_data_path / 'places.json'
        with open(places_file, 'w') as f:
            json.dump(self.sample_places, f)
        
        self.aggregator = DataAggregator(str(self.prepared_data_path))
    
    def tearDown(self):
        """Clean up"""
        self.temp_dir.cleanup()
    
    def test_city_has_correct_number_of_top_places(self):
        """Test that cities have exactly 20 top places (or less if fewer exist)"""
        self.aggregator.load_prepared_data()
        cities = self.aggregator.aggregate_cities()
        
        for city in cities:
            self.assertLessEqual(len(city.top_places), 20)
            self.assertEqual(len(city.top_places), min(20, city.place_count))
    
    def test_places_are_sorted_by_rank_score(self):
        """Test that places are sorted by rank_score in descending order"""
        self.aggregator.load_prepared_data()
        cities = self.aggregator.aggregate_cities()
        
        for city in cities:
            scores = [p.rank_score for p in city.top_places]
            self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_all_place_fields_preserved(self):
        """Test that all place fields are preserved during aggregation"""
        self.aggregator.load_prepared_data()
        cities = self.aggregator.aggregate_cities()
        
        for city in cities:
            for place in city.top_places:
                self.assertIsNotNone(place.name)
                self.assertIsNotNone(place.city)
                self.assertIsNotNone(place.state)
                self.assertIsNotNone(place.country)


if __name__ == '__main__':
    unittest.main()
