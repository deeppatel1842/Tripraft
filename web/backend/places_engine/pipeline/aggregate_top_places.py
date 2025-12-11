"""
Phase 1: Data Aggregation

Aggregates individual places into parent documents:
- Embeds top 20 places in each city document
- Embeds top 20 places in each state document
- Embeds top 5 places per state in country documents
- Generates search_text for full-text search

Input: prepared_data/places.json, prepared_data/cities.json, prepared_data/countries.json
Output: aggregated_data/ directory with optimized documents

Performance Impact:
- City view: 1 read instead of 21 reads (95% reduction)
- State view: 1 read instead of 21 reads (95% reduction)
- Country view: 11 reads instead of 211 reads (95% reduction)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import defaultdict
from dataclasses import asdict

from ..config import PlacesEngineConfig
from ..models import Place, City, State, Country, StateTopPlaces, Coordinates, PlaceOpeningHours, PlacePhoto

logger = logging.getLogger(__name__)


class DataAggregator:
    """
    Aggregates prepared place data into optimized documents.
    
    Creates:
    - Cities with top 20 embedded places
    - States with top 20 embedded places
    - Countries with states + top 5 places per state
    """
    
    # Configuration from config
    CITY_TOP_PLACES_COUNT = 20
    STATE_TOP_PLACES_COUNT = 20
    COUNTRY_PLACES_PER_STATE = 5
    
    def __init__(self, prepared_data_path: str = 'pipeline/prepared_data'):
        """
        Initialize DataAggregator.
        
        Args:
            prepared_data_path: Path to prepared data directory
        """
        self.config = PlacesEngineConfig()
        self.data_path = Path(prepared_data_path)
        self.output_path = self.config.ENGINE_DIR / 'pipeline' / 'aggregated_data'
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Data containers
        self.places: List[Dict] = []
        self.places_by_id: Dict[str, Dict] = {}
        self.places_by_city: Dict[str, List[Dict]] = defaultdict(list)
        self.places_by_state: Dict[str, List[Dict]] = defaultdict(list)
        self.places_by_country: Dict[str, List[Dict]] = defaultdict(list)
        
        self.stats = {
            'places_read': 0,
            'cities_created': 0,
            'states_created': 0,
            'countries_created': 0,
            'errors': 0,
        }
        
        logger.info(f"DataAggregator initialized")
        logger.info(f"Input path: {self.data_path}")
        logger.info(f"Output path: {self.output_path}")
    
    def load_prepared_data(self) -> bool:
        """
        Load prepared places data from JSON files.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            places_file = self.data_path / 'places.json'
            
            if not places_file.exists():
                logger.error(f"Places file not found: {places_file}")
                return False
            
            logger.info(f"Loading places from {places_file}...")
            
            with open(places_file, 'r', encoding='utf-8') as f:
                self.places = json.load(f)
            
            self.stats['places_read'] = len(self.places)
            logger.info(f"Loaded {len(self.places)} places")
            
            # Index places for faster lookup
            for place in self.places:
                place_id = place.get('id')
                if place_id:
                    self.places_by_id[place_id] = place
                    
                    # Group by location hierarchy
                    city = place.get('city', 'Unknown')
                    state = place.get('state', 'Unknown')
                    country = place.get('country', 'Unknown')
                    
                    self.places_by_city[city].append(place)
                    self.places_by_state[state].append(place)
                    self.places_by_country[country].append(place)
            
            logger.info(f"Indexed places: {len(self.places_by_id)} unique")
            logger.info(f"Cities: {len(self.places_by_city)}")
            logger.info(f"States: {len(self.places_by_state)}")
            logger.info(f"Countries: {len(self.places_by_country)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading prepared data: {e}")
            self.stats['errors'] += 1
            return False
    
    def _dict_to_place(self, place_dict: Dict) -> Place:
        """Convert dictionary to Place object"""
        try:
            # Handle coordinates
            coords = place_dict.get('coordinates', {})
            if isinstance(coords, dict):
                coordinates = Coordinates(
                    latitude=coords.get('latitude', 0),
                    longitude=coords.get('longitude', 0)
                )
            else:
                coordinates = Coordinates(0, 0)
            
            # Handle opening hours
            hours = place_dict.get('opening_hours')
            if isinstance(hours, dict):
                opening_hours = PlaceOpeningHours(
                    monday=hours.get('monday'),
                    tuesday=hours.get('tuesday'),
                    wednesday=hours.get('wednesday'),
                    thursday=hours.get('thursday'),
                    friday=hours.get('friday'),
                    saturday=hours.get('saturday'),
                    sunday=hours.get('sunday'),
                    notes=hours.get('notes'),
                )
            else:
                opening_hours = None
            
            # Handle photos
            photos = place_dict.get('photos', {})
            if isinstance(photos, dict):
                place_photo = PlacePhoto(
                    thumbnail_url=photos.get('thumbnail_url'),
                    thumbnail_width=photos.get('thumbnail_width'),
                    thumbnail_height=photos.get('thumbnail_height'),
                    attribution=photos.get('attribution'),
                    has_valid_photo=photos.get('has_valid_photo', False),
                )
            else:
                place_photo = PlacePhoto()
            
            return Place(
                id=place_dict.get('id', ''),
                name=place_dict.get('name', ''),
                name_normalized=place_dict.get('name_normalized'),
                city=place_dict.get('city', ''),
                city_normalized=place_dict.get('city_normalized'),
                state=place_dict.get('state', ''),
                state_normalized=place_dict.get('state_normalized'),
                country=place_dict.get('country', ''),
                country_normalized=place_dict.get('country_normalized'),
                coordinates=coordinates,
                has_coordinates=place_dict.get('has_coordinates', False),
                address=place_dict.get('address'),
                ai_summary=place_dict.get('ai_summary'),
                name_english=place_dict.get('name_english'),
                name_native=place_dict.get('name_native'),
                rating_tourist_priority=place_dict.get('rating_tourist_priority', 3.5),
                rating_traveler_experience=place_dict.get('rating_traveler_experience', 3.5),
                rank_score=place_dict.get('rank_score', 0.6),
                cost=place_dict.get('cost'),
                suggested_duration=place_dict.get('suggested_duration'),
                best_time_to_visit=place_dict.get('best_time_to_visit'),
                place_tip=place_dict.get('place_tip'),
                advanced_booking=place_dict.get('advanced_booking'),
                opening_hours=opening_hours,
                photos=place_photo,
                tags=place_dict.get('tags', []),
                search_text=place_dict.get('search_text'),
                official_website=place_dict.get('official_website'),
                sunrise_view=place_dict.get('sunrise_view', False),
                sunset_view=place_dict.get('sunset_view', False),
                sunrise_time=place_dict.get('sunrise_time'),
                sunset_time=place_dict.get('sunset_time'),
            )
        except Exception as e:
            logger.warning(f"Error converting place dict to Place object: {e}")
            # Return minimal place object if conversion fails
            return Place(
                id=place_dict.get('id', ''),
                name=place_dict.get('name', ''),
                city=place_dict.get('city', ''),
                state=place_dict.get('state', ''),
                country=place_dict.get('country', ''),
            )
    
    def _get_top_places(self, places_list: List[Dict], count: int) -> List[Place]:
        """
        Get top N places by rank_score.
        
        Args:
            places_list: List of place dictionaries
            count: Number of top places to return
        
        Returns:
            List of top Place objects
        """
        # Sort by rank_score descending
        sorted_places = sorted(
            places_list,
            key=lambda p: p.get('rank_score', 0),
            reverse=True
        )
        
        # Take top N and convert to Place objects
        top_places = sorted_places[:count]
        return [self._dict_to_place(p) for p in top_places]
    
    def aggregate_cities(self) -> List[City]:
        """
        Aggregate cities with embedded top 20 places.
        
        Returns:
            List of City objects
        """
        logger.info("Aggregating cities...")
        cities = []
        
        try:
            for city_name, places_list in self.places_by_city.items():
                if not places_list:
                    continue
                
                # Get first place to extract metadata
                first_place = places_list[0]
                
                # Create normalized ID
                city_id = first_place.get('city_normalized', city_name.lower().replace(' ', '_'))
                
                # Get top 20 places
                top_places = self._get_top_places(places_list, self.CITY_TOP_PLACES_COUNT)
                
                # Generate search text
                search_text = self._generate_search_text(
                    city_name,
                    first_place.get('state', ''),
                    first_place.get('country', ''),
                    top_places
                )
                
                city = City(
                    id=city_id,
                    name=city_name,
                    city_normalized=city_name.lower().replace(' ', '_'),
                    state=first_place.get('state', ''),
                    state_normalized=first_place.get('state_normalized', ''),
                    country=first_place.get('country', ''),
                    country_normalized=first_place.get('country_normalized', ''),
                    coordinates=Coordinates(
                        latitude=first_place.get('coordinates', {}).get('latitude', 0),
                        longitude=first_place.get('coordinates', {}).get('longitude', 0),
                    ),
                    place_count=len(places_list),
                    top_places=top_places,
                    search_text=search_text,
                    last_updated=self._get_timestamp(),
                )
                
                cities.append(city)
                self.stats['cities_created'] += 1
            
            logger.info(f"Aggregated {len(cities)} cities")
            return cities
            
        except Exception as e:
            logger.error(f"Error aggregating cities: {e}")
            self.stats['errors'] += 1
            return cities
    
    def aggregate_states(self) -> List[State]:
        """
        Aggregate states with embedded top 20 places.
        
        Returns:
            List of State objects
        """
        logger.info("Aggregating states...")
        states = []
        
        try:
            for state_name, places_list in self.places_by_state.items():
                if not places_list:
                    continue
                
                # Get first place to extract metadata
                first_place = places_list[0]
                
                # Create normalized ID
                state_id = first_place.get('state_normalized', state_name.lower().replace(' ', '_'))
                
                # Get top 20 places
                top_places = self._get_top_places(places_list, self.STATE_TOP_PLACES_COUNT)
                
                # Get unique cities in this state
                cities_in_state = set()
                for place in places_list:
                    cities_in_state.add(place.get('city', 'Unknown'))
                
                cities_list = [
                    {
                        'city_id': city.lower().replace(' ', '_'),
                        'city_name': city,
                        'place_count': len([p for p in places_list if p.get('city') == city])
                    }
                    for city in sorted(cities_in_state)
                ]
                
                # Generate search text
                search_text = self._generate_search_text(
                    state_name,
                    first_place.get('country', ''),
                    '',
                    top_places
                )
                
                state = State(
                    id=state_id,
                    name=state_name,
                    state_normalized=state_name.lower().replace(' ', '_'),
                    state_code=first_place.get('state_code'),
                    country=first_place.get('country', ''),
                    country_normalized=first_place.get('country_normalized', ''),
                    place_count=len(places_list),
                    city_count=len(cities_in_state),
                    cities=cities_list,
                    top_places=top_places,
                    search_text=search_text,
                    last_updated=self._get_timestamp(),
                )
                
                states.append(state)
                self.stats['states_created'] += 1
            
            logger.info(f"Aggregated {len(states)} states")
            return states
            
        except Exception as e:
            logger.error(f"Error aggregating states: {e}")
            self.stats['errors'] += 1
            return states
    
    def aggregate_countries(self) -> List[Country]:
        """
        Aggregate countries with states and top 5 places per state.
        
        Returns:
            List of Country objects
        """
        logger.info("Aggregating countries...")
        countries = []
        
        try:
            for country_name, places_list in self.places_by_country.items():
                if not places_list:
                    continue
                
                # Get first place to extract metadata
                first_place = places_list[0]
                
                # Create normalized ID
                country_id = first_place.get('country_normalized', country_name.lower().replace(' ', '_'))
                
                # Group places by state
                states_in_country: Dict[str, List[Dict]] = defaultdict(list)
                for place in places_list:
                    state = place.get('state', 'Unknown')
                    states_in_country[state].append(place)
                
                # Build states array with top 5 places per state
                states_array = []
                for state_name in sorted(states_in_country.keys()):
                    state_places = states_in_country[state_name]
                    top_state_places = self._get_top_places(state_places, self.COUNTRY_PLACES_PER_STATE)
                    
                    state_top = StateTopPlaces(
                        state_id=state_name.lower().replace(' ', '_'),
                        state_name=state_name,
                        place_count=len(state_places),
                        top_places=top_state_places,
                    )
                    states_array.append(state_top)
                
                # Generate search text
                search_text = self._generate_search_text(
                    country_name,
                    '',
                    '',
                    [p for state_places in states_array for p in state_places.top_places]
                )
                
                country = Country(
                    id=country_id,
                    name=country_name,
                    country_normalized=country_name.lower().replace(' ', '_'),
                    country_code=first_place.get('country_code'),
                    place_count=len(places_list),
                    state_count=len(states_in_country),
                    states=states_array,
                    search_text=search_text,
                    last_updated=self._get_timestamp(),
                )
                
                countries.append(country)
                self.stats['countries_created'] += 1
            
            logger.info(f"Aggregated {len(countries)} countries")
            return countries
            
        except Exception as e:
            logger.error(f"Error aggregating countries: {e}")
            self.stats['errors'] += 1
            return countries
    
    def _generate_search_text(
        self,
        name: str,
        parent1: str,
        parent2: str,
        places: List[Place]
    ) -> str:
        """
        Generate searchable text from aggregated data.
        
        Args:
            name: Primary name (city/state/country)
            parent1: Parent location (state/country or country)
            parent2: Additional context
            places: List of places for tag/summary extraction
        
        Returns:
            Searchable text string
        """
        parts = []
        
        # Add names
        parts.append(name.lower())
        if parent1:
            parts.append(parent1.lower())
        if parent2:
            parts.append(parent2.lower())
        
        # Add tags from places
        all_tags = set()
        for place in places:
            all_tags.update([tag.lower() for tag in (place.tags or [])])
        parts.extend(sorted(all_tags))
        
        # Join and deduplicate
        search_text = ' '.join(parts)
        unique_words = ' '.join(dict.fromkeys(search_text.split()))
        
        return unique_words
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
    
    def save_aggregated_data(
        self,
        cities: List[City],
        states: List[State],
        countries: List[Country]
    ) -> bool:
        """
        Save aggregated data to JSON files.
        
        Args:
            cities: List of City objects
            states: List of State objects
            countries: List of Country objects
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Saving aggregated data to {self.output_path}...")
            
            # Save cities
            cities_file = self.output_path / 'cities_aggregated.json'
            cities_data = [city.to_dict() for city in cities]
            with open(cities_file, 'w', encoding='utf-8') as f:
                json.dump(cities_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(cities)} cities to {cities_file}")
            
            # Save states
            states_file = self.output_path / 'states_aggregated.json'
            states_data = [state.to_dict() for state in states]
            with open(states_file, 'w', encoding='utf-8') as f:
                json.dump(states_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(states)} states to {states_file}")
            
            # Save countries
            countries_file = self.output_path / 'countries_aggregated.json'
            countries_data = [country.to_dict() for country in countries]
            with open(countries_file, 'w', encoding='utf-8') as f:
                json.dump(countries_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(countries)} countries to {countries_file}")
            
            # Save stats
            stats_file = self.output_path / 'aggregation_stats.json'
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2)
            logger.info(f"Saved statistics to {stats_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving aggregated data: {e}")
            self.stats['errors'] += 1
            return False
    
    def run(self) -> bool:
        """
        Execute full aggregation pipeline.
        
        Returns:
            True if successful
        """
        logger.info("=" * 60)
        logger.info("PHASE 1: DATA AGGREGATION")
        logger.info("=" * 60)
        
        # Load data
        if not self.load_prepared_data():
            return False
        
        # Aggregate
        cities = self.aggregate_cities()
        states = self.aggregate_states()
        countries = self.aggregate_countries()
        
        # Save
        if not self.save_aggregated_data(cities, states, countries):
            return False
        
        # Print summary
        logger.info("=" * 60)
        logger.info("AGGREGATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Places read: {self.stats['places_read']}")
        logger.info(f"Cities created: {self.stats['cities_created']}")
        logger.info(f"States created: {self.stats['states_created']}")
        logger.info(f"Countries created: {self.stats['countries_created']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("=" * 60)
        
        return self.stats['errors'] == 0


def main():
    """CLI entry point for Phase 1 aggregation"""
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    aggregator = DataAggregator()
    success = aggregator.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
