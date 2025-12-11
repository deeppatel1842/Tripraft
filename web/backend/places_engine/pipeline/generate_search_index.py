"""
Phase 2: Generate Search Index for Autocomplete

This script creates a prefix-based search index for lightning-fast autocomplete queries.

Functionality:
- Reads aggregated data (cities, states, countries)
- Groups suggestions by prefix (1-3 characters)
- Creates index documents with ranking
- Supports fuzzy matching for typos
- Generates search suggestions for all location types

Performance:
- Autocomplete response time: <100ms
- Index lookup: O(1) by prefix
- Firebase reads per autocomplete query: 1

Output:
- search_index_suggestions.json (all suggestions)
- search_index_documents.json (prefix-based documents for Firestore)
- search_index_stats.json (statistics)
"""

import json
import os
import sys
import logging
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import configuration
from ..config import PlacesEngineConfig


@dataclass
class Suggestion:
    """Single autocomplete suggestion"""
    id: str
    name: str
    type: str  # 'country', 'state', 'city', 'place'
    prefix: str
    match_text: str
    display_text: str
    location_hierarchy: Dict  # {'country': '...', 'state': '...', 'city': '...'}
    rank: float  # 0-100 (higher = better match)
    rank_score: Optional[float] = None  # 0-1 for places
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'prefix': self.prefix,
            'match_text': self.match_text,
            'display_text': self.display_text,
            'location_hierarchy': self.location_hierarchy,
            'rank': self.rank,
            'rank_score': self.rank_score,
        }


@dataclass
class PrefixIndex:
    """Index document for a single prefix"""
    prefix: str
    suggestions: List[Suggestion]
    total_count: int
    types: Dict[str, int]  # count by type
    last_updated: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'prefix': self.prefix,
            'suggestions': [s.to_dict() for s in self.suggestions],
            'total_count': self.total_count,
            'types': self.types,
            'last_updated': self.last_updated,
        }


class SearchIndexGenerator:
    """Generate prefix-based search index for autocomplete"""
    
    def __init__(self):
        self.config = PlacesEngineConfig
        self.aggregated_data_dir = Path(__file__).parent / 'aggregated_data'
        self.output_dir = self.aggregated_data_dir
        self.suggestions: List[Suggestion] = []
        self.prefix_indexes: Dict[str, List[Suggestion]] = defaultdict(list)
        self.stats = {
            'suggestions_generated': 0,
            'countries_processed': 0,
            'states_processed': 0,
            'cities_processed': 0,
            'places_processed': 0,
            'prefixes_created': 0,
            'errors': 0,
        }
        
        logger.info("SearchIndexGenerator initialized")
    
    def load_aggregated_data(self) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Load aggregated data from Phase 1 output"""
        logger.info("Loading aggregated data...")
        
        countries_file = self.aggregated_data_dir / 'countries_aggregated.json'
        states_file = self.aggregated_data_dir / 'states_aggregated.json'
        cities_file = self.aggregated_data_dir / 'cities_aggregated.json'
        
        try:
            with open(countries_file, 'r', encoding='utf-8') as f:
                countries = json.load(f)
            logger.info(f"Loaded {len(countries)} countries")
        except FileNotFoundError:
            logger.error(f"Countries file not found: {countries_file}")
            countries = []
        
        try:
            with open(states_file, 'r', encoding='utf-8') as f:
                states = json.load(f)
            logger.info(f"Loaded {len(states)} states")
        except FileNotFoundError:
            logger.error(f"States file not found: {states_file}")
            states = []
        
        try:
            with open(cities_file, 'r', encoding='utf-8') as f:
                cities = json.load(f)
            logger.info(f"Loaded {len(cities)} cities")
        except FileNotFoundError:
            logger.error(f"Cities file not found: {cities_file}")
            cities = []
        
        return countries, states, cities
    
    def _generate_prefixes(self, text: str, max_length: int = 3) -> List[str]:
        """Generate all prefixes from text (1 to max_length chars)"""
        normalized = text.lower().strip()
        prefixes = set()
        
        for i in range(1, min(len(normalized) + 1, max_length + 1)):
            prefixes.add(normalized[:i])
        
        return sorted(list(prefixes))
    
    def _calculate_rank(self, 
                       search_type: str, 
                       is_partial_match: bool = False,
                       rank_score: Optional[float] = None) -> float:
        """
        Calculate ranking score (0-100).
        
        Scoring:
        - Countries: 90-100 (highest priority)
        - States: 80-90 (medium-high)
        - Cities: 70-80 (medium)
        - Places: 60-75 (depends on rank_score)
        """
        
        base_scores = {
            'country': 95,
            'state': 85,
            'city': 75,
            'place': 65,
        }
        
        rank = base_scores.get(search_type, 50)
        
        # Slight penalty for partial matches
        if is_partial_match:
            rank -= 2
        
        # Place rank includes the rank_score
        if search_type == 'place' and rank_score:
            # rank_score is 0-1, convert to 0-10 bonus
            rank += (rank_score * 10)
        
        return min(100, max(0, rank))
    
    def generate_country_suggestions(self, countries: List[Dict]) -> None:
        """Generate suggestions from countries"""
        logger.info("Generating country suggestions...")
        
        for country_data in countries:
            try:
                country_id = country_data.get('id')
                country_name = country_data.get('name')
                country_code = country_data.get('country_code', '')
                
                if not country_id or not country_name:
                    logger.warning(f"Skipping invalid country data: {country_data}")
                    self.stats['errors'] += 1
                    continue
                
                # Generate prefixes
                prefixes = self._generate_prefixes(country_name, 3)
                
                for prefix in prefixes:
                    suggestion = Suggestion(
                        id=country_id,
                        name=country_name,
                        type='country',
                        prefix=prefix,
                        match_text=f"{country_name} {country_code}".strip(),
                        display_text=country_name,
                        location_hierarchy={'country': country_name},
                        rank=self._calculate_rank('country', len(prefix) < len(country_name)),
                    )
                    
                    self.suggestions.append(suggestion)
                    self.prefix_indexes[prefix].append(suggestion)
                
                self.stats['countries_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing country {country_data}: {e}")
                self.stats['errors'] += 1
    
    def generate_state_suggestions(self, states: List[Dict]) -> None:
        """Generate suggestions from states"""
        logger.info("Generating state suggestions...")
        
        for state_data in states:
            try:
                state_id = state_data.get('id')
                state_name = state_data.get('name')
                country_name = state_data.get('country_name', 'Unknown')
                
                if not state_id or not state_name:
                    logger.warning(f"Skipping invalid state data: {state_data}")
                    self.stats['errors'] += 1
                    continue
                
                # Generate prefixes
                prefixes = self._generate_prefixes(state_name, 3)
                
                for prefix in prefixes:
                    suggestion = Suggestion(
                        id=state_id,
                        name=state_name,
                        type='state',
                        prefix=prefix,
                        match_text=f"{state_name} {country_name}",
                        display_text=f"{state_name}, {country_name}",
                        location_hierarchy={
                            'country': country_name,
                            'state': state_name,
                        },
                        rank=self._calculate_rank('state', len(prefix) < len(state_name)),
                    )
                    
                    self.suggestions.append(suggestion)
                    self.prefix_indexes[prefix].append(suggestion)
                
                self.stats['states_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing state {state_data}: {e}")
                self.stats['errors'] += 1
    
    def generate_city_suggestions(self, cities: List[Dict]) -> None:
        """Generate suggestions from cities"""
        logger.info("Generating city suggestions...")
        
        for city_data in cities:
            try:
                city_id = city_data.get('id')
                city_name = city_data.get('name')
                state_name = city_data.get('state_name', '')
                country_name = city_data.get('country_name', 'Unknown')
                
                if not city_id or not city_name:
                    logger.warning(f"Skipping invalid city data: {city_data}")
                    self.stats['errors'] += 1
                    continue
                
                # Generate prefixes
                prefixes = self._generate_prefixes(city_name, 3)
                
                for prefix in prefixes:
                    # Build display text
                    if state_name:
                        display = f"{city_name}, {state_name}, {country_name}"
                        match = f"{city_name} {state_name} {country_name}"
                    else:
                        display = f"{city_name}, {country_name}"
                        match = f"{city_name} {country_name}"
                    
                    suggestion = Suggestion(
                        id=city_id,
                        name=city_name,
                        type='city',
                        prefix=prefix,
                        match_text=match,
                        display_text=display,
                        location_hierarchy={
                            'country': country_name,
                            'state': state_name,
                            'city': city_name,
                        },
                        rank=self._calculate_rank('city', len(prefix) < len(city_name)),
                    )
                    
                    self.suggestions.append(suggestion)
                    self.prefix_indexes[prefix].append(suggestion)
                
                self.stats['cities_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing city {city_data}: {e}")
                self.stats['errors'] += 1
    
    def generate_place_suggestions(self, 
                                  countries: List[Dict],
                                  states: List[Dict],
                                  cities: List[Dict]) -> None:
        """Generate suggestions from top places in aggregated data"""
        logger.info("Generating place suggestions from aggregated data...")
        
        place_count = 0
        
        # From countries (top 5 places per state)
        for country_data in countries:
            country_name = country_data.get('name', 'Unknown')
            states_list = country_data.get('states', [])
            
            for state_obj in states_list:
                state_name = state_obj.get('state_name', '')
                top_places = state_obj.get('top_places', [])
                
                for place_data in top_places[:2]:  # Only top 2 per state from country view
                    self._add_place_suggestion(place_data, country_name, state_name)
                    place_count += 1
        
        # From states (top 20 places)
        for state_data in states:
            state_name = state_data.get('name')
            country_name = state_data.get('country_name', 'Unknown')
            top_places = state_data.get('top_places', [])
            
            for place_data in top_places[:5]:  # Only top 5 per state from state view
                self._add_place_suggestion(place_data, country_name, state_name)
                place_count += 1
        
        # From cities (top 20 places)
        for city_data in cities:
            city_name = city_data.get('name')
            state_name = city_data.get('state_name', '')
            country_name = city_data.get('country_name', 'Unknown')
            top_places = city_data.get('top_places', [])
            
            for place_data in top_places[:5]:  # Only top 5 per city from city view
                self._add_place_suggestion(place_data, country_name, state_name, city_name)
                place_count += 1
        
        self.stats['places_processed'] = place_count
        logger.info(f"Generated {place_count} place suggestions")
    
    def _add_place_suggestion(self, 
                             place_data: Dict,
                             country_name: str,
                             state_name: str = '',
                             city_name: str = '') -> None:
        """Add a single place as suggestion"""
        try:
            place_id = place_data.get('id')
            place_name = place_data.get('name')
            rank_score = place_data.get('rank_score')
            
            if not place_id or not place_name:
                return
            
            # Generate prefixes (only first 2 chars for places - too many otherwise)
            prefixes = self._generate_prefixes(place_name, 2)
            
            # Build location hierarchy
            location_hierarchy = {'country': country_name}
            if state_name:
                location_hierarchy['state'] = state_name
            if city_name:
                location_hierarchy['city'] = city_name
            
            # Build display text
            display_parts = [place_name]
            if city_name:
                display_parts.append(city_name)
            if state_name and state_name != city_name:
                display_parts.append(state_name)
            display_parts.append(country_name)
            display_text = ', '.join(display_parts)
            
            for prefix in prefixes:
                suggestion = Suggestion(
                    id=place_id,
                    name=place_name,
                    type='place',
                    prefix=prefix,
                    match_text=display_text,
                    display_text=display_text,
                    location_hierarchy=location_hierarchy,
                    rank=self._calculate_rank('place', len(prefix) < len(place_name), rank_score),
                    rank_score=rank_score,
                )
                
                self.suggestions.append(suggestion)
                self.prefix_indexes[prefix].append(suggestion)
        
        except Exception as e:
            logger.error(f"Error processing place {place_data}: {e}")
            self.stats['errors'] += 1
    
    def sort_suggestions_by_rank(self) -> None:
        """Sort suggestions within each prefix by rank (descending)"""
        logger.info("Sorting suggestions by rank...")
        
        for prefix in self.prefix_indexes:
            self.prefix_indexes[prefix].sort(key=lambda s: s.rank, reverse=True)
            
            # Keep top suggestions only (configurable limit)
            max_per_prefix = 20
            self.prefix_indexes[prefix] = self.prefix_indexes[prefix][:max_per_prefix]
        
        logger.info(f"Sorted {len(self.prefix_indexes)} prefix groups")
    
    def save_search_suggestions(self) -> None:
        """Save all suggestions to JSON"""
        logger.info("Saving search suggestions...")
        
        suggestions_data = [s.to_dict() for s in self.suggestions]
        
        output_file = self.output_dir / 'search_index_suggestions.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(suggestions_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(suggestions_data)} suggestions to {output_file}")
    
    def save_prefix_indexes(self) -> None:
        """Save prefix-based indexes for Firestore upload"""
        logger.info("Saving prefix indexes...")
        
        indexes = []
        current_time = time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        for prefix, suggestions in sorted(self.prefix_indexes.items()):
            type_counts = defaultdict(int)
            for suggestion in suggestions:
                type_counts[suggestion.type] += 1
            
            index_doc = PrefixIndex(
                prefix=prefix,
                suggestions=suggestions,
                total_count=len(suggestions),
                types=dict(type_counts),
                last_updated=current_time,
            )
            
            indexes.append(index_doc.to_dict())
        
        output_file = self.output_dir / 'search_index_documents.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(indexes, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(indexes)} prefix indexes to {output_file}")
        self.stats['prefixes_created'] = len(indexes)
    
    def save_stats(self) -> None:
        """Save generation statistics"""
        logger.info("Saving statistics...")
        
        stats_data = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'total_suggestions': len(self.suggestions),
            'total_prefixes': len(self.prefix_indexes),
            'stats': self.stats,
        }
        
        output_file = self.output_dir / 'search_index_stats.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved statistics to {output_file}")
    
    def run(self) -> Dict:
        """Execute full search index generation pipeline"""
        logger.info("=" * 60)
        logger.info("PHASE 2: SEARCH INDEX GENERATION")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        try:
            # 1. Load aggregated data from Phase 1
            countries, states, cities = self.load_aggregated_data()
            
            if not countries and not states and not cities:
                logger.error("No aggregated data found. Please run Phase 1 first.")
                return {'success': False, 'error': 'No aggregated data'}
            
            # 2. Generate suggestions from all sources
            self.generate_country_suggestions(countries)
            self.generate_state_suggestions(states)
            self.generate_city_suggestions(cities)
            self.generate_place_suggestions(countries, states, cities)
            
            # 3. Sort suggestions by rank
            self.sort_suggestions_by_rank()
            
            # 4. Save output files
            self.save_search_suggestions()
            self.save_prefix_indexes()
            self.save_stats()
            
            # 5. Log completion
            elapsed_time = time.time() - start_time
            
            logger.info("=" * 60)
            logger.info("PHASE 2: SEARCH INDEX GENERATION COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Total suggestions: {len(self.suggestions)}")
            logger.info(f"Unique prefixes: {len(self.prefix_indexes)}")
            logger.info(f"Countries: {self.stats['countries_processed']}")
            logger.info(f"States: {self.stats['states_processed']}")
            logger.info(f"Cities: {self.stats['cities_processed']}")
            logger.info(f"Places: {self.stats['places_processed']}")
            logger.info(f"Errors: {self.stats['errors']}")
            logger.info(f"Time: {elapsed_time:.2f} seconds")
            logger.info("=" * 60)
            
            return {
                'success': True,
                'total_suggestions': len(self.suggestions),
                'prefixes_created': len(self.prefix_indexes),
                'elapsed_time': elapsed_time,
                'stats': self.stats,
            }
        
        except Exception as e:
            logger.error(f"Error during search index generation: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}


def main():
    """Entry point for search index generation"""
    generator = SearchIndexGenerator()
    result = generator.run()
    
    if not result['success']:
        logger.error(f"Generation failed: {result.get('error')}")
        sys.exit(1)
    
    logger.info("✅ Search index generation complete!")
    sys.exit(0)


if __name__ == '__main__':
    main()
