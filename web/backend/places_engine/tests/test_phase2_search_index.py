"""
Unit Tests for Phase 2: Search Index Generation

Test coverage:
- SearchIndexGenerator initialization
- Data loading and validation
- Prefix generation
- Ranking calculations
- Suggestion generation (countries, states, cities, places)
- Sorting and filtering
- File I/O operations
- Full pipeline execution
- Data consistency checks
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import sys
import os

# Add parent and grandparent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from places_engine.pipeline.generate_search_index import (
    SearchIndexGenerator,
    Suggestion,
    PrefixIndex,
)
from places_engine.config import PlacesEngineConfig


class TestSuggestionDataModel(unittest.TestCase):
    """Test Suggestion dataclass"""
    
    def test_suggestion_creation_basic(self):
        """Test creating a basic suggestion"""
        suggestion = Suggestion(
            id='country_1',
            name='France',
            type='country',
            prefix='f',
            match_text='France',
            display_text='France',
            location_hierarchy={'country': 'France'},
            rank=95.0,
        )
        
        self.assertEqual(suggestion.id, 'country_1')
        self.assertEqual(suggestion.name, 'France')
        self.assertEqual(suggestion.type, 'country')
        self.assertEqual(suggestion.rank, 95.0)
        self.assertIsNone(suggestion.rank_score)
    
    def test_suggestion_creation_with_rank_score(self):
        """Test creating a suggestion with rank_score for places"""
        suggestion = Suggestion(
            id='place_1',
            name='Eiffel Tower',
            type='place',
            prefix='ei',
            match_text='Eiffel Tower, Paris, France',
            display_text='Eiffel Tower, Paris, France',
            location_hierarchy={'country': 'France', 'city': 'Paris'},
            rank=78.5,
            rank_score=0.95,
        )
        
        self.assertEqual(suggestion.type, 'place')
        self.assertEqual(suggestion.rank_score, 0.95)
    
    def test_suggestion_to_dict(self):
        """Test suggestion conversion to dictionary"""
        suggestion = Suggestion(
            id='state_1',
            name='Texas',
            type='state',
            prefix='te',
            match_text='Texas, USA',
            display_text='Texas, USA',
            location_hierarchy={'country': 'USA', 'state': 'Texas'},
            rank=87.5,
        )
        
        result = suggestion.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['id'], 'state_1')
        self.assertEqual(result['type'], 'state')
        self.assertEqual(result['rank'], 87.5)


class TestPrefixIndexDataModel(unittest.TestCase):
    """Test PrefixIndex dataclass"""
    
    def test_prefix_index_creation(self):
        """Test creating a prefix index"""
        suggestions = [
            Suggestion('c1', 'Canada', 'country', 'c', 'Canada', 'Canada', {'country': 'Canada'}, 95),
            Suggestion('c2', 'China', 'country', 'c', 'China', 'China', {'country': 'China'}, 94),
        ]
        
        index = PrefixIndex(
            prefix='c',
            suggestions=suggestions,
            total_count=2,
            types={'country': 2},
            last_updated='2025-12-08T00:00:00Z',
        )
        
        self.assertEqual(index.prefix, 'c')
        self.assertEqual(len(index.suggestions), 2)
        self.assertEqual(index.total_count, 2)
        self.assertEqual(index.types['country'], 2)
    
    def test_prefix_index_to_dict(self):
        """Test prefix index conversion to dictionary"""
        suggestions = [
            Suggestion('s1', 'Singapore', 'city', 's', 'Singapore', 'Singapore', {'country': 'Singapore'}, 75),
        ]
        
        index = PrefixIndex(
            prefix='s',
            suggestions=suggestions,
            total_count=1,
            types={'city': 1},
            last_updated='2025-12-08T00:00:00Z',
        )
        
        result = index.to_dict()
        
        self.assertEqual(result['prefix'], 's')
        self.assertEqual(len(result['suggestions']), 1)
        self.assertEqual(result['total_count'], 1)


class TestSearchIndexGeneratorInitialization(unittest.TestCase):
    """Test SearchIndexGenerator initialization and setup"""
    
    def test_generator_initialization(self):
        """Test generator initialization with default settings"""
        generator = SearchIndexGenerator()
        
        self.assertIsNotNone(generator.config)
        self.assertIsInstance(generator.suggestions, list)
        self.assertEqual(len(generator.suggestions), 0)
        self.assertEqual(generator.stats['suggestions_generated'], 0)
    
    def test_generator_stats_initialization(self):
        """Test that stats are properly initialized"""
        generator = SearchIndexGenerator()
        
        expected_keys = [
            'suggestions_generated',
            'countries_processed',
            'states_processed',
            'cities_processed',
            'places_processed',
            'prefixes_created',
            'errors',
        ]
        
        for key in expected_keys:
            self.assertIn(key, generator.stats)


class TestPrefixGeneration(unittest.TestCase):
    """Test prefix generation logic"""
    
    def setUp(self):
        self.generator = SearchIndexGenerator()
    
    def test_generate_prefixes_single_char(self):
        """Test prefix generation for single character"""
        prefixes = self.generator._generate_prefixes('a')
        self.assertEqual(prefixes, ['a'])
    
    def test_generate_prefixes_single_word(self):
        """Test prefix generation for single word"""
        prefixes = self.generator._generate_prefixes('france', 3)
        
        self.assertIn('f', prefixes)
        self.assertIn('fr', prefixes)
        self.assertIn('fra', prefixes)
        self.assertEqual(len(prefixes), 3)
    
    def test_generate_prefixes_multiple_words(self):
        """Test prefix generation with multiple words"""
        prefixes = self.generator._generate_prefixes('new york', 3)
        
        # Should normalize to lowercase and start from beginning
        self.assertIn('n', prefixes)
        self.assertIn('ne', prefixes)
        self.assertIn('new', prefixes)
    
    def test_generate_prefixes_case_insensitive(self):
        """Test that prefix generation is case insensitive"""
        prefixes1 = self.generator._generate_prefixes('FRANCE')
        prefixes2 = self.generator._generate_prefixes('france')
        
        self.assertEqual(prefixes1, prefixes2)
    
    def test_generate_prefixes_with_whitespace(self):
        """Test prefix generation handles whitespace"""
        prefixes = self.generator._generate_prefixes('  france  ', 3)
        
        # Should strip whitespace
        self.assertIn('f', prefixes)
        self.assertNotIn(' ', prefixes[0])


class TestRankingCalculation(unittest.TestCase):
    """Test ranking score calculations"""
    
    def setUp(self):
        self.generator = SearchIndexGenerator()
    
    def test_rank_country_full_match(self):
        """Test ranking for country with full match"""
        rank = self.generator._calculate_rank('country', is_partial_match=False)
        
        self.assertGreaterEqual(rank, 90)
        self.assertLessEqual(rank, 100)
    
    def test_rank_state_full_match(self):
        """Test ranking for state with full match"""
        rank = self.generator._calculate_rank('state', is_partial_match=False)
        
        self.assertGreaterEqual(rank, 80)
        self.assertLess(rank, 90)
    
    def test_rank_city_full_match(self):
        """Test ranking for city with full match"""
        rank = self.generator._calculate_rank('city', is_partial_match=False)
        
        self.assertGreaterEqual(rank, 70)
        self.assertLess(rank, 80)
    
    def test_rank_place_with_score(self):
        """Test ranking for place with rank_score"""
        rank = self.generator._calculate_rank('place', is_partial_match=False, rank_score=0.95)
        
        # Should be base (65) + rank_score bonus (9.5) = ~74.5
        self.assertGreaterEqual(rank, 70)
        self.assertLess(rank, 80)
    
    def test_rank_partial_match_penalty(self):
        """Test that partial matches get ranking penalty"""
        rank_full = self.generator._calculate_rank('country', is_partial_match=False)
        rank_partial = self.generator._calculate_rank('country', is_partial_match=True)
        
        # Partial should be 2 points lower
        self.assertEqual(rank_full - rank_partial, 2)
    
    def test_rank_bounds(self):
        """Test that ranks stay within 0-100"""
        # Test with high rank_score
        rank_high = self.generator._calculate_rank('place', rank_score=1.0)
        self.assertLessEqual(rank_high, 100)
        
        # Test with invalid type
        rank_invalid = self.generator._calculate_rank('unknown')
        self.assertGreaterEqual(rank_invalid, 0)
        self.assertLessEqual(rank_invalid, 100)


class TestSuggestionGeneration(unittest.TestCase):
    """Test suggestion generation for different location types"""
    
    def setUp(self):
        self.generator = SearchIndexGenerator()
    
    def test_generate_country_suggestions_basic(self):
        """Test generating suggestions from country data"""
        countries = [
            {
                'id': 'france',
                'name': 'France',
                'country_code': 'FR',
            }
        ]
        
        self.generator.generate_country_suggestions(countries)
        
        self.assertEqual(self.generator.stats['countries_processed'], 1)
        self.assertGreater(len(self.generator.suggestions), 0)
        
        # Should have suggestions for 'f', 'fr', 'fra'
        france_suggestions = [s for s in self.generator.suggestions if s.id == 'france']
        self.assertEqual(len(france_suggestions), 3)
    
    def test_generate_state_suggestions_basic(self):
        """Test generating suggestions from state data"""
        states = [
            {
                'id': 'texas',
                'name': 'Texas',
                'country_name': 'USA',
            }
        ]
        
        self.generator.generate_state_suggestions(states)
        
        self.assertEqual(self.generator.stats['states_processed'], 1)
        self.assertGreater(len(self.generator.suggestions), 0)
        
        # Should have 'Texas' in display text
        texas_suggestions = [s for s in self.generator.suggestions if s.id == 'texas']
        self.assertGreater(len(texas_suggestions), 0)
        self.assertIn('USA', texas_suggestions[0].display_text)
    
    def test_generate_city_suggestions_basic(self):
        """Test generating suggestions from city data"""
        cities = [
            {
                'id': 'paris',
                'name': 'Paris',
                'state_name': 'Île-de-France',
                'country_name': 'France',
            }
        ]
        
        self.generator.generate_city_suggestions(cities)
        
        self.assertEqual(self.generator.stats['cities_processed'], 1)
        paris_suggestions = [s for s in self.generator.suggestions if s.id == 'paris']
        self.assertGreater(len(paris_suggestions), 0)
    
    def test_generate_city_suggestions_without_state(self):
        """Test generating city suggestions when state is missing"""
        cities = [
            {
                'id': 'singapore',
                'name': 'Singapore',
                'state_name': '',
                'country_name': 'Singapore',
            }
        ]
        
        self.generator.generate_city_suggestions(cities)
        
        singapore_suggestions = [s for s in self.generator.suggestions if s.id == 'singapore']
        self.assertGreater(len(singapore_suggestions), 0)
    
    def test_generate_place_suggestions_from_aggregated_data(self):
        """Test generating place suggestions from aggregated data"""
        countries = [
            {
                'id': 'france',
                'name': 'France',
                'states': [
                    {
                        'state_name': 'Île-de-France',
                        'top_places': [
                            {
                                'id': 'place_1',
                                'name': 'Eiffel Tower',
                                'rank_score': 0.98,
                            }
                        ]
                    }
                ]
            }
        ]
        
        self.generator.generate_place_suggestions(countries, [], [])
        
        place_suggestions = [s for s in self.generator.suggestions if s.type == 'place']
        self.assertGreater(len(place_suggestions), 0)


class TestSortingAndFiltering(unittest.TestCase):
    """Test sorting and filtering of suggestions"""
    
    def setUp(self):
        self.generator = SearchIndexGenerator()
    
    def test_sort_suggestions_by_rank(self):
        """Test that suggestions are sorted by rank descending"""
        # Add suggestions with different ranks
        self.generator.suggestions = [
            Suggestion('a', 'Alpha', 'country', 'a', 'Alpha', 'Alpha', {}, 60),
            Suggestion('b', 'Beta', 'country', 'b', 'Beta', 'Beta', {}, 95),
            Suggestion('c', 'Charlie', 'country', 'c', 'Charlie', 'Charlie', {}, 70),
            Suggestion('d', 'Delta', 'country', 'd', 'Delta', 'Delta', {}, 90),
        ]
        
        # Add to prefix indexes
        for s in self.generator.suggestions:
            self.generator.prefix_indexes[s.prefix].append(s)
        
        self.generator.sort_suggestions_by_rank()
        
        # Check that each prefix is sorted
        for prefix_suggestions in self.generator.prefix_indexes.values():
            ranks = [s.rank for s in prefix_suggestions]
            self.assertEqual(ranks, sorted(ranks, reverse=True))
    
    def test_sort_limits_suggestions_per_prefix(self):
        """Test that suggestions are limited per prefix"""
        # Add many suggestions for same prefix
        for i in range(25):
            s = Suggestion(
                f'place_{i}', f'Place {i}', 'place', 'p', 
                f'Place {i}', f'Place {i}', {}, 50 + i
            )
            self.generator.suggestions.append(s)
            self.generator.prefix_indexes['p'].append(s)
        
        self.generator.sort_suggestions_by_rank()
        
        # Should be limited to 20
        self.assertLessEqual(len(self.generator.prefix_indexes['p']), 20)


class TestFileIO(unittest.TestCase):
    """Test file I/O operations"""
    
    def setUp(self):
        self.generator = SearchIndexGenerator()
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.generator.output_dir = Path(self.temp_dir)
    
    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_save_search_suggestions(self):
        """Test saving suggestions to JSON file"""
        self.generator.suggestions = [
            Suggestion('france', 'France', 'country', 'f', 'France', 'France', {'country': 'France'}, 95),
        ]
        
        self.generator.save_search_suggestions()
        
        output_file = self.generator.output_dir / 'search_index_suggestions.json'
        self.assertTrue(output_file.exists())
        
        # Verify content
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], 'france')
    
    def test_save_prefix_indexes(self):
        """Test saving prefix indexes to JSON file"""
        suggestions = [
            Suggestion('france', 'France', 'country', 'f', 'France', 'France', {'country': 'France'}, 95),
        ]
        self.generator.prefix_indexes['f'] = suggestions
        
        self.generator.save_prefix_indexes()
        
        output_file = self.generator.output_dir / 'search_index_documents.json'
        self.assertTrue(output_file.exists())
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['prefix'], 'f')
    
    def test_save_stats(self):
        """Test saving statistics to JSON file"""
        self.generator.stats['countries_processed'] = 100
        self.generator.stats['states_processed'] = 200
        
        self.generator.save_stats()
        
        output_file = self.generator.output_dir / 'search_index_stats.json'
        self.assertTrue(output_file.exists())
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data['stats']['countries_processed'], 100)
        self.assertEqual(data['stats']['states_processed'], 200)


class TestDataConsistency(unittest.TestCase):
    """Test data consistency in search index"""
    
    def setUp(self):
        self.generator = SearchIndexGenerator()
    
    def test_all_suggestions_have_valid_type(self):
        """Test that all suggestions have valid types"""
        valid_types = {'country', 'state', 'city', 'place'}
        
        self.generator.suggestions = [
            Suggestion('a', 'A', 'country', 'a', 'A', 'A', {}, 90),
            Suggestion('b', 'B', 'state', 'b', 'B', 'B', {}, 80),
            Suggestion('c', 'C', 'city', 'c', 'C', 'C', {}, 70),
            Suggestion('d', 'D', 'place', 'd', 'D', 'D', {}, 60),
        ]
        
        for suggestion in self.generator.suggestions:
            self.assertIn(suggestion.type, valid_types)
    
    def test_all_suggestions_have_required_fields(self):
        """Test that all suggestions have required fields"""
        self.generator.suggestions = [
            Suggestion('id', 'Name', 'country', 'p', 'Match', 'Display', {'country': 'C'}, 90),
        ]
        
        for suggestion in self.generator.suggestions:
            self.assertIsNotNone(suggestion.id)
            self.assertIsNotNone(suggestion.name)
            self.assertIsNotNone(suggestion.type)
            self.assertIsNotNone(suggestion.prefix)
            self.assertIsNotNone(suggestion.match_text)
            self.assertIsNotNone(suggestion.display_text)
            self.assertIsNotNone(suggestion.rank)
    
    def test_ranks_are_in_valid_range(self):
        """Test that all rank values are in 0-100 range"""
        self.generator.suggestions = [
            Suggestion('a', 'A', 'country', 'a', 'A', 'A', {}, 95),
            Suggestion('b', 'B', 'state', 'b', 'B', 'B', {}, 85),
            Suggestion('c', 'C', 'city', 'c', 'C', 'C', {}, 75),
        ]
        
        for suggestion in self.generator.suggestions:
            self.assertGreaterEqual(suggestion.rank, 0)
            self.assertLessEqual(suggestion.rank, 100)


class TestFullPipeline(unittest.TestCase):
    """Test full search index generation pipeline"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = SearchIndexGenerator()
        self.generator.output_dir = Path(self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    @patch.object(SearchIndexGenerator, 'load_aggregated_data')
    def test_full_run_with_mock_data(self, mock_load):
        """Test full pipeline execution with mock data"""
        # Setup mock data
        mock_load.return_value = (
            [
                {
                    'id': 'france',
                    'name': 'France',
                    'country_code': 'FR',
                    'states': [
                        {
                            'state_name': 'Île-de-France',
                            'top_places': [
                                {'id': 'p1', 'name': 'Eiffel Tower', 'rank_score': 0.98}
                            ]
                        }
                    ]
                }
            ],
            [
                {
                    'id': 'texas',
                    'name': 'Texas',
                    'country_name': 'USA',
                    'top_places': [
                        {'id': 'p2', 'name': 'The Alamo', 'rank_score': 0.95}
                    ]
                }
            ],
            [
                {
                    'id': 'paris',
                    'name': 'Paris',
                    'state_name': 'Île-de-France',
                    'country_name': 'France',
                    'top_places': [
                        {'id': 'p3', 'name': 'Louvre', 'rank_score': 0.97}
                    ]
                }
            ]
        )
        
        result = self.generator.run()
        
        self.assertTrue(result['success'])
        self.assertGreater(result['total_suggestions'], 0)
        self.assertGreater(result['prefixes_created'], 0)


def run_tests():
    """Run all tests with verbose output"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSuggestionDataModel))
    suite.addTests(loader.loadTestsFromTestCase(TestPrefixIndexDataModel))
    suite.addTests(loader.loadTestsFromTestCase(TestSearchIndexGeneratorInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestPrefixGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestRankingCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestSuggestionGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestSortingAndFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestFileIO))
    suite.addTests(loader.loadTestsFromTestCase(TestDataConsistency))
    suite.addTests(loader.loadTestsFromTestCase(TestFullPipeline))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
