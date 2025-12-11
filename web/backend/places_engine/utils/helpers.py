"""
Places Engine Utility Helpers

Common utility functions used across the places engine.
"""

import math
import re
from typing import Dict, Optional, Tuple, List


def normalize_string(value: str) -> str:
    """
    Normalize a string for consistent matching.
    
    - Converts to lowercase
    - Replaces spaces with underscores
    - Removes special characters
    
    Args:
        value: String to normalize
    
    Returns:
        Normalized string
    """
    if not value:
        return ''
    
    # Lowercase and strip
    normalized = value.lower().strip()
    
    # Remove special characters except spaces
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    
    # Replace spaces with underscores
    normalized = '_'.join(normalized.split())
    
    return normalized


def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate the great-circle distance between two points using Haversine formula.
    
    Args:
        lat1: Latitude of first point (degrees)
        lon1: Longitude of first point (degrees)
        lat2: Latitude of second point (degrees)
        lon2: Longitude of second point (degrees)
    
    Returns:
        Distance in meters
    """
    earth_radius = 6371000  # Earth radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (
        math.sin(delta_phi / 2) ** 2 +
        math.cos(phi1) * math.cos(phi2) *
        math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return earth_radius * c


def calculate_bounding_box(
    latitude: float,
    longitude: float,
    radius_meters: float
) -> Dict[str, float]:
    """
    Calculate a bounding box for geospatial queries.
    
    Args:
        latitude: Center latitude (degrees)
        longitude: Center longitude (degrees)
        radius_meters: Radius in meters
    
    Returns:
        Dict with min_lat, max_lat, min_lng, max_lng
    """
    # 1 degree latitude ≈ 111km
    lat_delta = (radius_meters / 1000) / 111
    
    # 1 degree longitude ≈ 111km * cos(latitude)
    lng_delta = (radius_meters / 1000) / (111 * math.cos(math.radians(latitude)))
    
    return {
        'min_lat': latitude - lat_delta,
        'max_lat': latitude + lat_delta,
        'min_lng': longitude - lng_delta,
        'max_lng': longitude + lng_delta
    }


def validate_coordinates(
    latitude: Optional[float],
    longitude: Optional[float]
) -> Tuple[bool, Optional[str]]:
    """
    Validate latitude and longitude coordinates.
    
    Args:
        latitude: Latitude value to validate
        longitude: Longitude value to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if latitude is None or longitude is None:
        return False, "Coordinates are required"
    
    try:
        lat = float(latitude)
        lng = float(longitude)
    except (ValueError, TypeError):
        return False, "Coordinates must be numeric"
    
    if not -90 <= lat <= 90:
        return False, "Latitude must be between -90 and 90"
    
    if not -180 <= lng <= 180:
        return False, "Longitude must be between -180 and 180"
    
    return True, None


def generate_search_text(place: Dict) -> str:
    """
    Generate searchable text from place data for text search.
    
    Combines name, city, state, country, tags, and description
    into a single normalized string.
    
    Args:
        place: Place dictionary
    
    Returns:
        Searchable text string
    """
    parts = []
    
    # Add core fields
    for field in ['name', 'city', 'state', 'country']:
        value = place.get(field)
        if value:
            parts.append(str(value).lower())
    
    # Add tags
    tags = place.get('tags', [])
    if tags:
        parts.extend(str(tag).lower() for tag in tags)
    
    # Add description snippet
    description = place.get('description', '')
    if description:
        # Take first 200 characters
        parts.append(description[:200].lower())
    
    return ' '.join(parts)


def format_distance(meters: float) -> str:
    """
    Format distance in human-readable format.
    
    Args:
        meters: Distance in meters
    
    Returns:
        Formatted string (e.g., "1.5 km", "500 m")
    """
    if meters >= 1000:
        return f"{meters / 1000:.1f} km"
    return f"{int(meters)} m"


def sort_places_by_distance(
    places: List[Dict],
    reference_lat: float,
    reference_lng: float
) -> List[Dict]:
    """
    Sort places by distance from a reference point.
    
    Args:
        places: List of place dictionaries
        reference_lat: Reference latitude
        reference_lng: Reference longitude
    
    Returns:
        Sorted list with distance_m field added
    """
    for place in places:
        coords = place.get('coordinates', {})
        place_lat = coords.get('latitude')
        place_lng = coords.get('longitude')
        
        if place_lat and place_lng:
            distance = calculate_distance(
                reference_lat, reference_lng,
                place_lat, place_lng
            )
            place['distance_m'] = round(distance, 2)
        else:
            place['distance_m'] = float('inf')
    
    return sorted(places, key=lambda p: p['distance_m'])


def chunk_list(items: List, chunk_size: int) -> List[List]:
    """
    Split a list into chunks of specified size.
    
    Useful for batch operations.
    
    Args:
        items: List to split
        chunk_size: Maximum items per chunk
    
    Returns:
        List of chunks
    """
    return [
        items[i:i + chunk_size]
        for i in range(0, len(items), chunk_size)
    ]


def merge_place_updates(
    existing: Dict,
    updates: Dict,
    overwrite: bool = False
) -> Dict:
    """
    Merge updates into existing place data.
    
    Args:
        existing: Existing place data
        updates: New data to merge
        overwrite: If True, overwrites existing values; if False, only fills gaps
    
    Returns:
        Merged place data
    """
    result = existing.copy()
    
    for key, value in updates.items():
        if value is not None:
            if overwrite or key not in result or result[key] is None:
                result[key] = value
    
    return result
