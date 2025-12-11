"""
Place Data Models

Represents the standardized structure for places data across all levels:
- City level: 20 top places embedded
- State level: 20 top places embedded  
- Country level: 5 top places per state embedded
- Individual place: Complete details for detail view

All models follow the official PLACE_SCHEMA from config.py
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class PlacePhoto:
    """Photo metadata for a place"""
    thumbnail_url: Optional[str] = None
    thumbnail_width: Optional[int] = None
    thumbnail_height: Optional[int] = None
    attribution: Optional[Dict] = None
    has_valid_photo: bool = False


@dataclass
class PlaceOpeningHours:
    """Opening hours by day of week"""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class Coordinates:
    """Geographic coordinates"""
    latitude: float
    longitude: float


@dataclass
class Place:
    """
    Complete place object with all information.
    
    Used in:
    - Individual place detail view (all fields)
    - City/State top_places arrays (all fields)
    - Country state top_places arrays (all fields)
    """
    # Core identifiers
    id: str
    name: str
    
    # Location hierarchy
    city: str
    state: str
    country: str
    
    # Optional core identifiers
    name_normalized: Optional[str] = None
    city_normalized: Optional[str] = None
    state_normalized: Optional[str] = None
    country_normalized: Optional[str] = None
    
    # Geolocation
    coordinates: Coordinates = field(default_factory=lambda: Coordinates(0, 0))
    has_coordinates: bool = False
    address: Optional[str] = None
    
    # Content
    ai_summary: Optional[str] = None
    name_english: Optional[str] = None
    name_native: Optional[str] = None
    
    # Ratings & Rankings
    rating_tourist_priority: float = 3.5
    rating_traveler_experience: float = 3.5
    rank_score: float = 0.6
    
    # Practical Info
    cost: Optional[str] = None
    suggested_duration: Optional[str] = None
    best_time_to_visit: Optional[str] = None
    place_tip: Optional[str] = None
    advanced_booking: Optional[str] = None
    opening_hours: Optional[PlaceOpeningHours] = None
    
    # Media
    photos: Optional[PlacePhoto] = None
    
    # Search & Filtering
    tags: List[str] = field(default_factory=list)
    search_text: Optional[str] = None
    
    # Additional Info
    official_website: Optional[str] = None
    sunrise_view: bool = False
    sunset_view: bool = False
    sunrise_time: Optional[str] = None
    sunset_time: Optional[str] = None
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling nested objects"""
        data = asdict(self)
        
        # Handle coordinates
        if isinstance(self.coordinates, Coordinates):
            data['coordinates'] = {
                'latitude': self.coordinates.latitude,
                'longitude': self.coordinates.longitude
            }
        
        # Handle opening hours
        if isinstance(self.opening_hours, PlaceOpeningHours):
            data['opening_hours'] = {
                'monday': self.opening_hours.monday,
                'tuesday': self.opening_hours.tuesday,
                'wednesday': self.opening_hours.wednesday,
                'thursday': self.opening_hours.thursday,
                'friday': self.opening_hours.friday,
                'saturday': self.opening_hours.saturday,
                'sunday': self.opening_hours.sunday,
                'notes': self.opening_hours.notes,
            }
        
        # Handle photos
        if isinstance(self.photos, PlacePhoto):
            data['photos'] = {
                'thumbnail_url': self.photos.thumbnail_url,
                'thumbnail_width': self.photos.thumbnail_width,
                'thumbnail_height': self.photos.thumbnail_height,
                'attribution': self.photos.attribution,
                'has_valid_photo': self.photos.has_valid_photo,
            }
        
        return data


@dataclass
class City:
    """
    City document with embedded top 20 places.
    
    Used in: City detail view
    Performance: 1 Firestore read = 1 city + 20 places
    """
    id: str
    name: str
    state: str
    country: str
    
    # Optional identifiers
    city_normalized: Optional[str] = None
    state_normalized: Optional[str] = None
    country_normalized: Optional[str] = None
    
    # Geo
    coordinates: Coordinates = field(default_factory=lambda: Coordinates(0, 0))
    
    # Data
    place_count: int = 0
    top_places: List[Place] = field(default_factory=list)  # Top 20 places
    
    # Search
    search_text: Optional[str] = None
    
    # Metadata
    last_updated: Optional[str] = None
    cache_ttl: int = 14400  # 4 hours
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'city_normalized': self.city_normalized,
            'state': self.state,
            'state_normalized': self.state_normalized,
            'country': self.country,
            'country_normalized': self.country_normalized,
            'coordinates': {
                'latitude': self.coordinates.latitude,
                'longitude': self.coordinates.longitude,
            },
            'place_count': self.place_count,
            'top_places': [p.to_dict() for p in self.top_places],
            'search_text': self.search_text,
            'metadata': {
                'last_updated': self.last_updated,
                'cache_ttl': self.cache_ttl,
            }
        }


@dataclass
class StateTopPlaces:
    """Container for state top places"""
    state_id: str
    state_name: str
    place_count: int
    top_places: List[Place] = field(default_factory=list)  # Top 5 places


@dataclass
class State:
    """
    State/Province document with embedded top 20 places.
    
    Used in: State detail view
    Performance: 1 Firestore read = 1 state + 20 places
    """
    id: str
    name: str
    country: str
    
    # Optional identifiers
    state_normalized: Optional[str] = None
    state_code: Optional[str] = None
    country_normalized: Optional[str] = None
    
    # Data
    place_count: int = 0
    city_count: int = 0
    cities: List[Dict] = field(default_factory=list)  # [{city_id, city_name, place_count}]
    top_places: List[Place] = field(default_factory=list)  # Top 20 places
    
    # Search
    search_text: Optional[str] = None
    
    # Metadata
    last_updated: Optional[str] = None
    cache_ttl: int = 14400  # 4 hours
    
    def __post_init__(self):
        """Auto-calculate city_count from cities list if not provided"""
        if self.city_count == 0 and self.cities:
            self.city_count = len(self.cities)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'state_normalized': self.state_normalized,
            'state_code': self.state_code,
            'country': self.country,
            'country_normalized': self.country_normalized,
            'place_count': self.place_count,
            'city_count': self.city_count,
            'cities': self.cities,
            'top_places': [p.to_dict() for p in self.top_places],
            'search_text': self.search_text,
            'metadata': {
                'last_updated': self.last_updated,
                'cache_ttl': self.cache_ttl,
            }
        }


@dataclass
class Country:
    """
    Country document with embedded states (each state has top 5 places).
    
    Used in: Country detail view showing all states with their top places
    Performance: 1 Firestore read = 1 country + 10 states + (10 * 5) places = 50 places
    """
    id: str
    name: str
    
    # Optional identifiers
    country_normalized: Optional[str] = None
    country_code: Optional[str] = None
    
    # Data
    place_count: int = 0
    state_count: int = 0
    states: List[StateTopPlaces] = field(default_factory=list)  # Each state with top 5 places
    
    # Search
    search_text: Optional[str] = None
    
    # Metadata
    last_updated: Optional[str] = None
    cache_ttl: int = 86400  # 24 hours
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'country_normalized': self.country_normalized,
            'country_code': self.country_code,
            'place_count': self.place_count,
            'state_count': self.state_count,
            'states': [
                {
                    'state_id': s.state_id,
                    'state_name': s.state_name,
                    'place_count': s.place_count,
                    'top_places': [p.to_dict() for p in s.top_places],
                }
                for s in self.states
            ],
            'search_text': self.search_text,
            'metadata': {
                'last_updated': self.last_updated,
                'cache_ttl': self.cache_ttl,
            }
        }


# Convenience type aliases
PlaceDict = Dict[str, Any]
PlacesList = List[Place]
