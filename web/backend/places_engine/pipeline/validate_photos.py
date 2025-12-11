"""
Places Engine Photo Validator

Validates and optionally fixes photo URLs in the dataset.
Identifies placeholder images, broken URLs, and missing photos.

Usage:
    from places_engine.pipeline import PhotoValidator
    
    validator = PhotoValidator(dataset_path='path/to/dataset')
    results = validator.run()
    validator.save_report('photo_report.json')
"""

import json
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from ..config import PlacesEngineConfig

logger = logging.getLogger(__name__)


@dataclass
class PhotoValidationResult:
    """Result of photo URL validation."""
    file_path: str
    total_places: int = 0
    valid_photos: int = 0
    invalid_photos: int = 0
    missing_photos: int = 0
    invalid_details: List[Dict] = field(default_factory=list)
    modified: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'file': self.file_path,
            'total_places': self.total_places,
            'valid_photos': self.valid_photos,
            'invalid_photos': self.invalid_photos,
            'missing_photos': self.missing_photos,
            'invalid_details': self.invalid_details,
            'modified': self.modified,
            'error': self.error
        }


class PhotoValidator:
    """
    Validator for photo URLs in places dataset.
    
    Identifies:
    - Placeholder images (logos, icons, flags)
    - Invalid file extensions
    - Missing photos
    - Inaccessible URLs (optional)
    """
    
    def __init__(
        self,
        dataset_path: Optional[str] = None,
        config: Optional[PlacesEngineConfig] = None
    ):
        """
        Initialize PhotoValidator.
        
        Args:
            dataset_path: Path to dataset directory
            config: PlacesEngineConfig instance
        """
        self.config = config or PlacesEngineConfig()
        self.dataset_path = Path(dataset_path or self.config.dataset_path)
        self.results: List[PhotoValidationResult] = []
        
        # Invalid patterns from config
        self.invalid_patterns = list(self.config.INVALID_PHOTO_PATTERNS)
        
        # Valid image extensions
        self.valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    
    def is_invalid_url(self, url: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Check if photo URL is invalid.
        
        Args:
            url: Photo URL to validate
        
        Returns:
            Tuple of (is_invalid, reason)
        """
        if not url:
            return True, "missing_url"
        
        url_lower = url.lower()
        
        # Check against invalid patterns
        for pattern in self.invalid_patterns:
            if pattern in url_lower:
                return True, f"placeholder:{pattern}"
        
        # Check for SVG files
        if '.svg' in url_lower:
            return True, "svg_file"
        
        # Check for valid extensions
        has_valid_ext = any(ext in url_lower for ext in self.valid_extensions)
        if not has_valid_ext:
            return True, "invalid_extension"
        
        return False, None
    
    def test_url_accessible(
        self,
        url: str,
        timeout: int = 10
    ) -> Tuple[bool, Optional[str]]:
        """
        Test if URL is accessible.
        
        Args:
            url: URL to test
            timeout: Request timeout in seconds
        
        Returns:
            Tuple of (is_accessible, error_message)
        """
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                return True, None
            return False, f"status:{response.status_code}"
        except requests.exceptions.Timeout:
            return False, "timeout"
        except requests.exceptions.ConnectionError:
            return False, "connection_error"
        except Exception as e:
            return False, f"error:{type(e).__name__}"
    
    def extract_photo_url(self, photos: Optional[Dict]) -> Optional[str]:
        """Extract photo URL from photos object."""
        if not photos:
            return None
        
        # Try wikimedia_commons structure
        if 'wikimedia_commons' in photos:
            wikimedia = photos['wikimedia_commons']
            if isinstance(wikimedia, dict):
                thumbnail = wikimedia.get('thumbnail', {})
                if isinstance(thumbnail, dict):
                    return thumbnail.get('url')
        
        # Try direct thumbnail_url
        if 'thumbnail_url' in photos:
            return photos['thumbnail_url']
        
        # Try thumbnail directly
        if 'thumbnail' in photos:
            thumbnail = photos['thumbnail']
            if isinstance(thumbnail, dict):
                return thumbnail.get('url')
            return thumbnail
        
        return None
    
    def process_file(
        self,
        filepath: Path,
        fix: bool = False
    ) -> PhotoValidationResult:
        """
        Process a single JSON file.
        
        Args:
            filepath: Path to JSON file
            fix: If True, set invalid URLs to null
        
        Returns:
            PhotoValidationResult
        """
        result = PhotoValidationResult(file_path=str(filepath))
        
        # Read file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            result.error = str(e)
            return result
        
        modified = False
        
        for city_data in data.get('cities', []):
            city_name = city_data.get('city', 'Unknown')
            
            for place in city_data.get('places', []):
                result.total_places += 1
                place_name = place.get('name', 'Unknown')
                
                photos = place.get('photos')
                url = self.extract_photo_url(photos)
                
                if not url:
                    result.missing_photos += 1
                    result.invalid_details.append({
                        'place': place_name,
                        'city': city_name,
                        'reason': 'missing',
                        'url': None
                    })
                    continue
                
                is_invalid, reason = self.is_invalid_url(url)
                
                if is_invalid:
                    result.invalid_photos += 1
                    result.invalid_details.append({
                        'place': place_name,
                        'city': city_name,
                        'reason': reason,
                        'url': url
                    })
                    
                    if fix:
                        # Fix the photo data
                        if 'wikimedia_commons' in place.get('photos', {}):
                            place['photos']['wikimedia_commons']['thumbnail']['url'] = None
                            place['photos']['wikimedia_commons']['thumbnail']['invalid_reason'] = reason
                        else:
                            place['photos'] = {
                                'thumbnail_url': None,
                                'has_valid_photo': False,
                                'invalid_reason': reason,
                                'original_url': url
                            }
                        modified = True
                else:
                    result.valid_photos += 1
        
        # Save if modified
        if fix and modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            result.modified = True
        
        return result
    
    def run(self, fix: bool = False) -> Dict:
        """
        Run validation on entire dataset.
        
        Args:
            fix: If True, fix invalid URLs in place
        
        Returns:
            Dict with validation summary
        """
        self.results = []
        
        # Find JSON files
        json_files = list(self.dataset_path.rglob('*.json'))
        json_files = [
            f for f in json_files
            if not any(x in str(f) for x in ['.before_fix', 'prepared_data', 'report'])
        ]
        
        logger.info(f"Validating {len(json_files)} JSON files...")
        
        totals = {
            'files': 0,
            'total_places': 0,
            'valid_photos': 0,
            'invalid_photos': 0,
            'missing_photos': 0,
            'files_modified': 0
        }
        
        for filepath in sorted(json_files):
            result = self.process_file(filepath, fix=fix)
            self.results.append(result)
            
            totals['files'] += 1
            totals['total_places'] += result.total_places
            totals['valid_photos'] += result.valid_photos
            totals['invalid_photos'] += result.invalid_photos
            totals['missing_photos'] += result.missing_photos
            if result.modified:
                totals['files_modified'] += 1
        
        # Collect invalid patterns
        invalid_patterns = {}
        for result in self.results:
            for detail in result.invalid_details:
                reason = detail.get('reason', 'unknown')
                invalid_patterns[reason] = invalid_patterns.get(reason, 0) + 1
        
        return {
            'summary': totals,
            'invalid_patterns': invalid_patterns,
            'file_results': [r.to_dict() for r in self.results]
        }
    
    def test_urls_batch(
        self,
        urls: List[str],
        max_workers: int = 10
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Test multiple URLs in parallel.
        
        Args:
            urls: List of URLs to test
            max_workers: Maximum concurrent requests
        
        Returns:
            Dict mapping URL to (is_accessible, error)
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self.test_url_accessible, url): url
                for url in urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    is_accessible, error = future.result()
                    results[url] = (is_accessible, error)
                except Exception as e:
                    results[url] = (False, f"exception:{e}")
        
        return results
    
    def save_report(self, output_path: Optional[str] = None) -> None:
        """
        Save validation report.
        
        Args:
            output_path: Path for report file
        """
        if not self.results:
            raise RuntimeError("Run validation first with run()")
        
        output_path = output_path or 'photo_validation_report.json'
        
        totals = {
            'files': len(self.results),
            'total_places': sum(r.total_places for r in self.results),
            'valid_photos': sum(r.valid_photos for r in self.results),
            'invalid_photos': sum(r.invalid_photos for r in self.results),
            'missing_photos': sum(r.missing_photos for r in self.results),
            'files_modified': sum(1 for r in self.results if r.modified)
        }
        
        invalid_patterns = {}
        for result in self.results:
            for detail in result.invalid_details:
                reason = detail.get('reason', 'unknown')
                invalid_patterns[reason] = invalid_patterns.get(reason, 0) + 1
        
        report = {
            'summary': totals,
            'invalid_patterns': invalid_patterns,
            'file_results': [r.to_dict() for r in self.results]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Report saved to: {output_path}")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate photo URLs')
    parser.add_argument('--path', default='../dataset/countries', help='Path to dataset')
    parser.add_argument('--fix', action='store_true', help='Fix invalid URLs')
    parser.add_argument('--output', default='photo_validation_report.json', help='Output file')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    validator = PhotoValidator(dataset_path=args.path)
    results = validator.run(fix=args.fix)
    validator.save_report(args.output)
    
    # Print summary
    s = results['summary']
    print(f"\nValidation complete:")
    print(f"  Valid photos: {s['valid_photos']}")
    print(f"  Invalid photos: {s['invalid_photos']}")
    print(f"  Missing photos: {s['missing_photos']}")


if __name__ == '__main__':
    main()
