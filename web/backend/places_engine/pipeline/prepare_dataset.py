"""
Places Engine Dataset Preparer

Validates, normalizes, and prepares place data for Firestore upload.

Features:
- Validate JSON schema
- Generate unique place IDs
- Normalize field names and values
- Filter invalid photos
- Generate search text for full-text search

Usage:
    from places_engine.pipeline import DatasetPreparer
    
    preparer = DatasetPreparer(dataset_path='path/to/dataset')
    results = preparer.run()
    preparer.save('prepared_data/')
"""

import json
import hashlib
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

from ..config import PlacesEngineConfig

logger = logging.getLogger(__name__)


@dataclass
class PreparedPlace:
    """A prepared place document."""
    id: str
    data: Dict
    
    def to_dict(self) -> Dict:
        return {'id': self.id, **self.data}


class DatasetPreparer:
    """
    Prepares dataset for Firestore upload.
    
    Normalizes, validates, and transforms place data
    into the final upload format.
    """
    
    # Default values for missing fields
    FIELD_DEFAULTS = {
        'rating_tourist_priority': 3.5,
        'rating_traveler_experience': 3.5,
        'rank_score': 0.6,
        'cost': 'Varies',
        'suggested_duration': '1-2 hours',
        'best_time_to_visit': 'Year-round',
        'advanced_booking': 'Not required',
        'tags': [],
    }
    
    def __init__(
        self,
        dataset_path: Optional[str] = None,
        config: Optional[PlacesEngineConfig] = None
    ):
        """
        Initialize DatasetPreparer.
        
        Args:
            dataset_path: Path to dataset directory
            config: PlacesEngineConfig instance
        """
        self.config = config or PlacesEngineConfig()
        self.dataset_path = Path(dataset_path or self.config.dataset_path)
        
        self.places: List[PreparedPlace] = []
        self.cities: Dict[str, Dict] = {}
        self.countries: Dict[str, Dict] = {}
        self.stats = {
            'files_processed': 0,
            'places_processed': 0,
            'places_skipped': 0,
            'cities_created': 0,
            'countries_created': 0
        }
        
        # Invalid photo patterns
        self.invalid_photo_patterns = list(self.config.INVALID_PHOTO_PATTERNS)
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for consistent storage."""
        if not text:
            return ''
        return ' '.join(text.lower().split())
    
    def normalize_id(self, text: str) -> str:
        """Create normalized ID from text."""
        if not text:
            return ''
        normalized = re.sub(r'[^a-z0-9]+', '_', text.lower())
        return normalized.strip('_')
    
    def generate_place_id(
        self,
        country: str,
        city: str,
        place_name: str
    ) -> str:
        """Generate unique place ID."""
        country_id = self.normalize_id(country)[:20]
        city_id = self.normalize_id(city)[:30]
        place_id = self.normalize_id(place_name)[:50]
        
        full_id = f"{country_id}_{city_id}_{place_id}"
        
        if len(full_id) > 100:
            hash_suffix = hashlib.md5(full_id.encode()).hexdigest()[:8]
            full_id = f"{full_id[:90]}_{hash_suffix}"
        
        return full_id
    
    def is_valid_photo_url(self, url: Optional[str]) -> bool:
        """Check if photo URL is valid."""
        if not url:
            return False
        
        url_lower = url.lower()
        
        for pattern in self.invalid_photo_patterns:
            if pattern in url_lower:
                return False
        
        if '.svg' in url_lower:
            return False
        
        return True
    
    def sanitize_photos(self, photos: Optional[Dict]) -> Dict:
        """Sanitize photo object."""
        result = {
            'thumbnail_url': None,
            'thumbnail_width': None,
            'thumbnail_height': None,
            'attribution': None,
            'has_valid_photo': False
        }
        
        if not photos:
            return result
        
        # Extract URL from different structures
        url = None
        if 'wikimedia_commons' in photos:
            wikimedia = photos.get('wikimedia_commons', {})
            if isinstance(wikimedia, dict):
                thumbnail = wikimedia.get('thumbnail', {})
                if isinstance(thumbnail, dict):
                    url = thumbnail.get('url')
                    result['thumbnail_width'] = thumbnail.get('width')
                    result['thumbnail_height'] = thumbnail.get('height')
                    result['attribution'] = thumbnail.get('attribution')
        elif 'thumbnail_url' in photos:
            url = photos.get('thumbnail_url')
            result['thumbnail_width'] = photos.get('thumbnail_width')
            result['thumbnail_height'] = photos.get('thumbnail_height')
            result['attribution'] = photos.get('attribution')
        
        if url and self.is_valid_photo_url(url):
            result['thumbnail_url'] = url
            result['has_valid_photo'] = True
        
        return result
    
    def generate_search_text(self, place: Dict) -> str:
        """Generate searchable text from place data."""
        parts = []
        
        for field_name in ['name', 'city', 'state', 'country']:
            value = place.get(field_name)
            if value:
                parts.append(str(value).lower())
        
        tags = place.get('tags', [])
        if tags:
            parts.extend(str(tag).lower() for tag in tags)
        
        summary = place.get('ai_summary', '')
        if summary:
            parts.append(summary[:200].lower())
        
        return ' '.join(parts)
    
    def prepare_place(
        self,
        place: Dict,
        city: str,
        state: str,
        country: str
    ) -> Optional[PreparedPlace]:
        """Prepare a single place for upload."""
        name = place.get('name', '').strip()
        if not name:
            return None
        
        place_id = self.generate_place_id(country, city, name)
        
        # Build normalized document
        doc = {
            'name': name,
            'city': city,
            'state': state,
            'country': country,
            'city_normalized': self.normalize_id(city),
            'state_normalized': self.normalize_id(state),
            'country_normalized': self.normalize_id(country)
        }
        
        # Copy standard fields
        for field_name in [
            'ai_summary', 'why_visit', 'address', 'official_website',
            'cost', 'suggested_duration', 'best_time_to_visit',
            'advanced_booking', 'opening_hours', 'tags',
            'rating_tourist_priority', 'rating_traveler_experience',
            'rank_score'
        ]:
            value = place.get(field_name)
            if value is not None:
                doc[field_name] = value
            elif field_name in self.FIELD_DEFAULTS:
                doc[field_name] = self.FIELD_DEFAULTS[field_name]
        
        # Handle coordinates
        coords = place.get('coordinates', {})
        if coords and coords.get('latitude') is not None and coords.get('longitude') is not None:
            doc['coordinates'] = {
                'latitude': float(coords['latitude']),
                'longitude': float(coords['longitude'])
            }
            doc['has_coordinates'] = True
        else:
            doc['coordinates'] = None
            doc['has_coordinates'] = False
        
        # Sanitize photos
        doc['photos'] = self.sanitize_photos(place.get('photos'))
        
        # Generate search text
        doc['search_text'] = self.generate_search_text(doc)
        
        return PreparedPlace(id=place_id, data=doc)
    
    def process_file(self, filepath: Path) -> Dict:
        """Process a single JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            return {'error': str(e)}
        
        country = data.get('country', 'Unknown')
        state = data.get('state', 'Unknown')
        
        # Track country
        country_id = self.normalize_id(country)
        if country_id not in self.countries:
            self.countries[country_id] = {
                'id': country_id,
                'name': country,
                'name_normalized': country_id,
                'states': [],
                'place_count': 0
            }
            self.stats['countries_created'] += 1
        
        places_added = 0
        places_skipped = 0
        
        for city_data in data.get('cities', []):
            city_name = city_data.get('city', 'Unknown')
            city_id = self.generate_place_id(country, city_name, '')
            
            # Track city
            if city_id not in self.cities:
                self.cities[city_id] = {
                    'id': city_id,
                    'name': city_name,
                    'name_normalized': self.normalize_id(city_name),
                    'state': state,
                    'country': country,
                    'place_count': 0
                }
                self.stats['cities_created'] += 1
                
                # Add state to country
                if state not in [s['name'] for s in self.countries[country_id]['states']]:
                    self.countries[country_id]['states'].append({
                        'name': state,
                        'name_normalized': self.normalize_id(state),
                        'cities': []
                    })
            
            for place in city_data.get('places', []):
                prepared = self.prepare_place(place, city_name, state, country)
                
                if prepared:
                    self.places.append(prepared)
                    places_added += 1
                    
                    # Update counts
                    self.cities[city_id]['place_count'] += 1
                    self.countries[country_id]['place_count'] += 1
                else:
                    places_skipped += 1
        
        self.stats['files_processed'] += 1
        self.stats['places_processed'] += places_added
        self.stats['places_skipped'] += places_skipped
        
        return {
            'file': str(filepath),
            'places_added': places_added,
            'places_skipped': places_skipped
        }
    
    def run(self) -> Dict:
        """
        Run preparation on entire dataset.
        
        Returns:
            Dict with preparation stats
        """
        # Find JSON files
        json_files = list(self.dataset_path.rglob('*.json'))
        json_files = [
            f for f in json_files
            if not any(x in str(f) for x in ['.before_fix', 'prepared_data', 'report'])
        ]
        
        logger.info(f"Processing {len(json_files)} files...")
        
        for filepath in sorted(json_files):
            self.process_file(filepath)
        
        return {
            'stats': self.stats,
            'places_count': len(self.places),
            'cities_count': len(self.cities),
            'countries_count': len(self.countries)
        }
    
    def save(self, output_dir: Optional[str] = None) -> None:
        """
        Save prepared data to output directory.
        
        Args:
            output_dir: Directory for output files
        """
        output_path = Path(output_dir or 'prepared_data')
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save places
        places_file = output_path / 'places.json'
        places_data = [p.to_dict() for p in self.places]
        with open(places_file, 'w', encoding='utf-8') as f:
            json.dump(places_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(places_data)} places to {places_file}")
        
        # Save cities
        cities_file = output_path / 'cities.json'
        with open(cities_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.cities.values()), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(self.cities)} cities to {cities_file}")
        
        # Save countries
        countries_file = output_path / 'countries.json'
        with open(countries_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.countries.values()), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(self.countries)} countries to {countries_file}")
        
        # Save stats
        stats_file = output_path / 'stats.json'
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump({
                'prepared_at': datetime.now().isoformat(),
                'stats': self.stats,
                'totals': {
                    'places': len(self.places),
                    'cities': len(self.cities),
                    'countries': len(self.countries)
                }
            }, f, ensure_ascii=False, indent=2)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Prepare dataset')
    parser.add_argument('--path', default='../dataset/countries', help='Path to dataset')
    parser.add_argument('--output', default='prepared_data', help='Output directory')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    preparer = DatasetPreparer(dataset_path=args.path)
    results = preparer.run()
    preparer.save(args.output)
    
    print(f"\nPreparation complete:")
    print(f"  Places: {results['places_count']}")
    print(f"  Cities: {results['cities_count']}")
    print(f"  Countries: {results['countries_count']}")


if __name__ == '__main__':
    main()
