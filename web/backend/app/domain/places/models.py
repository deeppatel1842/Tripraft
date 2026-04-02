"""
Place Search Models

Data models for place search results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Country:
    """Country model"""
    id: int
    country_name: str
    created_at: Optional[datetime] = None


@dataclass
class State:
    """State model"""
    id: int
    country_id: int
    state_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[datetime] = None


@dataclass
class City:
    """City model"""
    id: int
    state_id: int
    city_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[datetime] = None


@dataclass
class OpeningHours:
    """Opening hours model"""
    id: int
    place_id: int
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class Photo:
    """Photo model"""
    id: int
    place_id: int
    source_file: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_width: Optional[int] = None
    thumbnail_height: Optional[int] = None
    photo_title: Optional[str] = None
    photo_author: Optional[str] = None
    license: Optional[str] = None
    license_url: Optional[str] = None
    source_url: Optional[str] = None
    credit: Optional[str] = None
    usage_terms: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Place:
    """Place model with all fields from database"""
    id: int
    city_id: int
    place_name: str
    name_english: Optional[str] = None
    ai_summary: Optional[str] = None
    suggested_duration: Optional[str] = None
    best_time_to_visit: Optional[str] = None
    place_tip: Optional[str] = None
    advanced_booking: Optional[str] = None
    state_name: Optional[str] = None
    sunrise_view: bool = False
    sunset_view: bool = False
    sunrise_time: Optional[str] = None
    sunset_time: Optional[str] = None
    cost: Optional[str] = None
    rating_tourist_priority: Optional[int] = None
    rating_traveler_experience: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    official_website: Optional[str] = None
    rank_score: Optional[float] = None
    created_at: Optional[datetime] = None
    # Related data
    city_name: Optional[str] = None
    country_name: Optional[str] = None
    photo: Optional[Photo] = None
    photos: List[Photo] = field(default_factory=list)
    opening_hours: Optional[OpeningHours] = None
    tags: List[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        """Alias for place_name for convenience."""
        return self.place_name

    def to_dict(self) -> Dict[str, Any]:
        """Convert place to dictionary for API response"""
        return {
            'id': self.id,
            'name': self.place_name,
            'name_english': self.name_english,
            'city_name': self.city_name,
            'state_name': self.state_name,
            'country_name': self.country_name,
            'ai_summary': self.ai_summary,
            'suggested_duration': self.suggested_duration,
            'best_time_to_visit': self.best_time_to_visit,
            'place_tip': self.place_tip,
            'advanced_booking': self.advanced_booking,
            'sunrise_view': bool(self.sunrise_view),
            'sunset_view': bool(self.sunset_view),
            'sunrise_time': self.sunrise_time,
            'sunset_time': self.sunset_time,
            'cost': self.cost,
            'rating_tourist_priority': self.rating_tourist_priority,
            'rating_traveler_experience': self.rating_traveler_experience,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'official_website': self.official_website,
            'rank_score': self.rank_score,
            'photo_url': self.photo.thumbnail_url if self.photo else None,
            'photos': [
                {
                    'url': p.thumbnail_url,
                    'title': p.photo_title,
                    'author': p.photo_author,
                    'width': p.thumbnail_width,
                    'height': p.thumbnail_height,
                }
                for p in self.photos if p.thumbnail_url
            ],
            'tags': self.tags,
            'opening_hours': {
                'monday': self.opening_hours.monday,
                'tuesday': self.opening_hours.tuesday,
                'wednesday': self.opening_hours.wednesday,
                'thursday': self.opening_hours.thursday,
                'friday': self.opening_hours.friday,
                'saturday': self.opening_hours.saturday,
                'sunday': self.opening_hours.sunday,
                'notes': self.opening_hours.notes,
            } if self.opening_hours else None,
        }


@dataclass
class SearchResult:
    """Search result wrapper"""
    success: bool
    query: str
    match_type: str  # 'country', 'state', 'city', 'place'
    total_count: int
    places: List[Place]
    matched_location: Optional[Dict[str, Any]] = None
    response_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format"""
        return {
            'success': self.success,
            'query': self.query,
            'match_type': self.match_type,
            'total_count': self.total_count,
            'places': [p.to_dict() for p in self.places],
            'matched_location': self.matched_location,
            'response_time_ms': self.response_time_ms,
        }


@dataclass
class AutocompleteSuggestion:
    """Autocomplete suggestion model"""
    id: str
    name: str
    type: str  # 'country', 'state', 'city', 'place'
    parent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'parent': self.parent,
        }
