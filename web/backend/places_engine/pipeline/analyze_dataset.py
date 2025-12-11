"""
Places Engine Dataset Analyzer

Analyzes all JSON files in the dataset to identify data quality issues:
- Files with empty places arrays
- Files missing required fields
- Files with invalid photo URLs
- Files without coordinates
- Files without rank scores

Usage:
    from places_engine.pipeline import DatasetAnalyzer
    
    analyzer = DatasetAnalyzer(dataset_path='path/to/dataset')
    results = analyzer.run()
    analyzer.save_report('analysis_report.json')
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from ..config import PlacesEngineConfig

logger = logging.getLogger(__name__)


@dataclass
class PlaceAnalysis:
    """Analysis result for a single place."""
    missing_required: List[str] = field(default_factory=list)
    missing_important: List[str] = field(default_factory=list)
    invalid_photo: bool = False
    no_coordinates: bool = False
    no_rank_score: bool = False
    
    @property
    def is_complete(self) -> bool:
        return len(self.missing_required) == 0


@dataclass
class FileAnalysis:
    """Analysis result for a single file."""
    file_path: str
    filename: str
    country: str = "Unknown"
    state: str = "Unknown"
    status: str = "unknown"
    total_places: int = 0
    complete_places: int = 0
    incomplete_places: int = 0
    places_without_coords: int = 0
    places_without_rank: int = 0
    places_with_invalid_photo: int = 0
    is_empty: bool = False
    has_valid_structure: bool = True
    issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'file': self.file_path,
            'filename': self.filename,
            'country': self.country,
            'state': self.state,
            'status': self.status,
            'total_places': self.total_places,
            'complete_places': self.complete_places,
            'incomplete_places': self.incomplete_places,
            'places_without_coords': self.places_without_coords,
            'places_without_rank': self.places_without_rank,
            'places_with_invalid_photo': self.places_with_invalid_photo,
            'is_empty': self.is_empty,
            'has_valid_structure': self.has_valid_structure,
            'issues': self.issues
        }


class DatasetAnalyzer:
    """
    Analyzer for places dataset quality.
    
    Scans JSON files and generates reports on data completeness,
    missing fields, and invalid data.
    """
    
    # Required fields for a complete place
    REQUIRED_PLACE_FIELDS = [
        'name',
        'ai_summary',
        'coordinates',
        'tags',
        'cost',
        'rating_tourist_priority',
        'rating_traveler_experience',
    ]
    
    # Important but optional fields
    IMPORTANT_PLACE_FIELDS = [
        'rank_score',
        'photos',
        'opening_hours',
        'suggested_duration',
        'best_time_to_visit',
        'address',
        'official_website',
    ]
    
    def __init__(
        self,
        dataset_path: Optional[str] = None,
        config: Optional[PlacesEngineConfig] = None
    ):
        """
        Initialize DatasetAnalyzer.
        
        Args:
            dataset_path: Path to dataset directory
            config: PlacesEngineConfig instance
        """
        self.config = config or PlacesEngineConfig()
        self.dataset_path = Path(dataset_path or self.config.dataset_path)
        self.results: Optional[Dict] = None
        
        # Invalid photo patterns from config
        self.invalid_photo_patterns = list(self.config.INVALID_PHOTO_PATTERNS)
    
    def analyze_place(self, place: Dict) -> PlaceAnalysis:
        """Analyze a single place for data quality issues."""
        analysis = PlaceAnalysis()
        
        # Check required fields
        for field_name in self.REQUIRED_PLACE_FIELDS:
            value = place.get(field_name)
            if value is None or value == '' or value == []:
                analysis.missing_required.append(field_name)
        
        # Check coordinates
        coords = place.get('coordinates', {})
        if not coords or coords.get('latitude') is None:
            analysis.no_coordinates = True
        
        # Check rank_score
        if place.get('rank_score') is None:
            analysis.no_rank_score = True
            analysis.missing_important.append('rank_score')
        
        # Check photos
        photos = place.get('photos', {})
        if photos:
            url = self._extract_photo_url(photos)
            if url:
                url_lower = url.lower()
                for pattern in self.invalid_photo_patterns:
                    if pattern in url_lower:
                        analysis.invalid_photo = True
                        break
            else:
                analysis.missing_important.append('photos')
        else:
            analysis.missing_important.append('photos')
        
        # Check other important fields
        for field_name in self.IMPORTANT_PLACE_FIELDS:
            if field_name not in ['rank_score', 'photos']:
                if place.get(field_name) is None:
                    analysis.missing_important.append(field_name)
        
        return analysis
    
    def _extract_photo_url(self, photos: Dict) -> Optional[str]:
        """Extract photo URL from photos structure."""
        if 'wikimedia_commons' in photos:
            wikimedia = photos.get('wikimedia_commons', {})
            thumbnail = wikimedia.get('thumbnail', {}) if isinstance(wikimedia, dict) else {}
            return thumbnail.get('url') if isinstance(thumbnail, dict) else None
        return photos.get('thumbnail_url')
    
    def analyze_file(self, filepath: Path) -> FileAnalysis:
        """Analyze a single JSON file."""
        analysis = FileAnalysis(
            file_path=str(filepath),
            filename=filepath.name
        )
        
        # Read file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            analysis.status = 'error'
            analysis.has_valid_structure = False
            analysis.issues.append(f"JSON parse error: {e}")
            return analysis
        except Exception as e:
            analysis.status = 'error'
            analysis.has_valid_structure = False
            analysis.issues.append(f"Read error: {e}")
            return analysis
        
        # Extract metadata
        analysis.country = data.get('country', 'Unknown')
        analysis.state = data.get('state', 'Unknown')
        
        # Validate structure
        if 'cities' not in data:
            analysis.has_valid_structure = False
            analysis.issues.append("Missing 'cities' array")
        
        if not data.get('country'):
            analysis.issues.append("Missing 'country' field")
        
        if not data.get('state'):
            analysis.issues.append("Missing 'state' field")
        
        # Collect all places
        all_places = []
        for city_data in data.get('cities', []):
            city_name = city_data.get('city', 'Unknown')
            places = city_data.get('places', [])
            for place in places:
                all_places.append({'place': place, 'city': city_name})
        
        analysis.total_places = len(all_places)
        
        if len(all_places) == 0:
            analysis.is_empty = True
            analysis.status = 'empty'
            analysis.issues.append("No places in file")
            return analysis
        
        # Analyze each place
        for item in all_places:
            place_analysis = self.analyze_place(item['place'])
            
            if place_analysis.is_complete:
                analysis.complete_places += 1
            else:
                analysis.incomplete_places += 1
            
            if place_analysis.no_coordinates:
                analysis.places_without_coords += 1
            
            if place_analysis.no_rank_score:
                analysis.places_without_rank += 1
            
            if place_analysis.invalid_photo:
                analysis.places_with_invalid_photo += 1
        
        # Determine status
        if analysis.complete_places == analysis.total_places:
            analysis.status = 'complete'
        elif analysis.complete_places > 0:
            analysis.status = 'partial'
        else:
            analysis.status = 'incomplete'
        
        return analysis
    
    def run(self) -> Dict:
        """
        Run analysis on entire dataset.
        
        Returns:
            Dict with analysis results
        """
        results = {
            'analyzed_at': datetime.now().isoformat(),
            'base_path': str(self.dataset_path),
            'summary': {
                'total_files': 0,
                'complete_files': 0,
                'partial_files': 0,
                'incomplete_files': 0,
                'empty_files': 0,
                'error_files': 0,
                'total_places': 0,
                'complete_places': 0,
                'places_without_coords': 0,
                'places_without_rank': 0,
                'places_with_invalid_photo': 0
            },
            'by_country': {},
            'files': [],
            'empty_files': [],
            'incomplete_files': [],
            'error_files': []
        }
        
        # Find JSON files
        json_files = list(self.dataset_path.rglob('*.json'))
        json_files = [
            f for f in json_files
            if not any(x in str(f) for x in ['.before_fix', 'prepared_data', 'report'])
        ]
        
        logger.info(f"Analyzing {len(json_files)} JSON files...")
        
        for filepath in sorted(json_files):
            file_result = self.analyze_file(filepath)
            results['files'].append(file_result.to_dict())
            
            # Update summary
            summary = results['summary']
            summary['total_files'] += 1
            summary['total_places'] += file_result.total_places
            summary['complete_places'] += file_result.complete_places
            summary['places_without_coords'] += file_result.places_without_coords
            summary['places_without_rank'] += file_result.places_without_rank
            summary['places_with_invalid_photo'] += file_result.places_with_invalid_photo
            
            # Categorize file
            if file_result.status == 'complete':
                summary['complete_files'] += 1
            elif file_result.status == 'partial':
                summary['partial_files'] += 1
                results['incomplete_files'].append(file_result.to_dict())
            elif file_result.status == 'empty':
                summary['empty_files'] += 1
                results['empty_files'].append(file_result.to_dict())
            elif file_result.status == 'error':
                summary['error_files'] += 1
                results['error_files'].append(file_result.to_dict())
            else:
                summary['incomplete_files'] += 1
                results['incomplete_files'].append(file_result.to_dict())
            
            # Track by country
            country = file_result.country
            if country not in results['by_country']:
                results['by_country'][country] = {
                    'files': 0,
                    'places': 0,
                    'complete': 0,
                    'empty': 0
                }
            results['by_country'][country]['files'] += 1
            results['by_country'][country]['places'] += file_result.total_places
            if file_result.status == 'complete':
                results['by_country'][country]['complete'] += 1
            if file_result.is_empty:
                results['by_country'][country]['empty'] += 1
        
        self.results = results
        return results
    
    def save_report(
        self,
        output_path: Optional[str] = None,
        include_text: bool = True
    ) -> None:
        """
        Save analysis report to files.
        
        Args:
            output_path: Path for JSON report
            include_text: Also generate text report
        """
        if not self.results:
            raise RuntimeError("Run analysis first with run()")
        
        output_path = output_path or 'analysis_report.json'
        
        # Save JSON report
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON report saved to: {output_path}")
        
        # Save text report
        if include_text:
            text_path = output_path.replace('.json', '.txt')
            text_report = self.generate_text_report()
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text_report)
            logger.info(f"Text report saved to: {text_path}")
    
    def generate_text_report(self) -> str:
        """Generate human-readable text report."""
        if not self.results:
            return "No analysis results available. Run analysis first."
        
        lines = []
        s = self.results['summary']
        
        lines.append("=" * 80)
        lines.append("PLACES DATASET ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {self.results['analyzed_at']}")
        lines.append(f"Dataset: {self.results['base_path']}")
        lines.append("")
        
        # Summary
        lines.append("-" * 40)
        lines.append("SUMMARY")
        lines.append("-" * 40)
        total = s['total_files']
        lines.append(f"Total Files: {total}")
        lines.append(f"  Complete: {s['complete_files']} ({100*s['complete_files']/total:.1f}%)")
        lines.append(f"  Partial: {s['partial_files']} ({100*s['partial_files']/total:.1f}%)")
        lines.append(f"  Empty: {s['empty_files']} ({100*s['empty_files']/total:.1f}%)")
        lines.append(f"  Error: {s['error_files']}")
        lines.append("")
        
        total_places = s['total_places']
        lines.append(f"Total Places: {total_places}")
        if total_places > 0:
            lines.append(f"  Complete: {s['complete_places']} ({100*s['complete_places']/total_places:.1f}%)")
        lines.append(f"  Without Coords: {s['places_without_coords']}")
        lines.append(f"  Without Rank: {s['places_without_rank']}")
        lines.append(f"  Invalid Photos: {s['places_with_invalid_photo']}")
        lines.append("")
        
        # By country
        lines.append("-" * 40)
        lines.append("BY COUNTRY")
        lines.append("-" * 40)
        for country, stats in sorted(
            self.results['by_country'].items(),
            key=lambda x: -x[1]['places']
        ):
            empty_note = f" ({stats['empty']} empty)" if stats['empty'] > 0 else ""
            lines.append(f"  {country}: {stats['files']} files, {stats['places']} places{empty_note}")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze places dataset')
    parser.add_argument('--path', default='../dataset/countries', help='Path to dataset')
    parser.add_argument('--output', default='analysis_report.json', help='Output file')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    analyzer = DatasetAnalyzer(dataset_path=args.path)
    results = analyzer.run()
    analyzer.save_report(args.output)
    
    # Print summary
    s = results['summary']
    print(f"\nAnalysis complete:")
    print(f"  Files: {s['total_files']} total, {s['complete_files']} complete, {s['empty_files']} empty")
    print(f"  Places: {s['total_places']} total, {s['complete_places']} complete")


if __name__ == '__main__':
    main()
