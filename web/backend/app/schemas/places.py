"""
Place Ingestion Schemas (Pydantic v2)
======================================
Single source of truth for all data validation in the ingestion pipeline.
Used by admin API endpoints, CLI tools, and bulk import.
"""

import math
from typing import List, Literal, Optional

from pydantic import (BaseModel, Field, HttpUrl, field_validator,
                      model_validator)

# ---------------------------------------------------------------------------
# Geo helpers
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two lat/lon points."""
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Create / Write schemas
# ---------------------------------------------------------------------------

class CountryCreate(BaseModel):
    """Schema for creating a country."""
    country_name: str = Field(..., min_length=2, max_length=200)


class StateCreate(BaseModel):
    """Schema for creating a state."""
    country_id: int = Field(..., gt=0)
    state_name: str = Field(..., min_length=2, max_length=200)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class CityCreate(BaseModel):
    """Schema for creating a city."""
    state_id: int = Field(..., gt=0)
    city_name: str = Field(..., min_length=2, max_length=200)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class PlaceCreate(BaseModel):
    """Core schema for ingesting a single place."""
    city_id: int = Field(..., gt=0, description="FK to cities table")
    place_name: str = Field(..., min_length=2, max_length=300)
    name_english: Optional[str] = Field(None, max_length=300)
    ai_summary: Optional[str] = Field(None, max_length=5000)
    suggested_duration: Optional[str] = Field(None, max_length=100)
    best_time_to_visit: Optional[str] = Field(None, max_length=200)
    place_tip: Optional[str] = Field(None, max_length=2000)
    advanced_booking: Optional[str] = Field(None, max_length=100)
    state_name: Optional[str] = Field(None, max_length=200)
    sunrise_view: bool = False
    sunset_view: bool = False
    sunrise_time: Optional[str] = Field(None, max_length=50)
    sunset_time: Optional[str] = Field(None, max_length=50)
    cost: Optional[Literal["free", "low", "medium", "high"]] = None
    rating_tourist_priority: Optional[int] = Field(None, ge=1, le=5)
    rating_traveler_experience: Optional[int] = Field(None, ge=1, le=5)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)
    official_website: Optional[str] = Field(None, max_length=500)
    rank_score: Optional[float] = Field(None, ge=0.0, le=5.0)

    @field_validator("official_website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            v = v.strip()
            if not v.startswith(("http://", "https://")):
                raise ValueError("Website must start with http:// or https://")
        return v or None

    @model_validator(mode="after")
    def lat_lon_pair(self):
        """Latitude and longitude must both be present or both absent."""
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must both be provided or both omitted")
        return self


class PhotoCreate(BaseModel):
    """Schema for creating a photo."""
    place_id: int = Field(..., gt=0)
    thumbnail_url: str = Field(..., min_length=10, max_length=1000)
    thumbnail_width: Optional[int] = Field(None, ge=1)
    thumbnail_height: Optional[int] = Field(None, ge=1)
    photo_title: Optional[str] = Field(None, max_length=500)
    photo_author: Optional[str] = Field(None, max_length=300)
    license: Optional[str] = Field(None, max_length=200)
    license_url: Optional[str] = Field(None, max_length=1000)
    source_url: Optional[str] = Field(None, max_length=1000)
    credit: Optional[str] = Field(None, max_length=500)
    usage_terms: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)

    @field_validator("thumbnail_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class OpeningHoursCreate(BaseModel):
    """Schema for creating opening hours."""
    place_id: int = Field(..., gt=0)
    monday: Optional[str] = Field(None, max_length=100)
    tuesday: Optional[str] = Field(None, max_length=100)
    wednesday: Optional[str] = Field(None, max_length=100)
    thursday: Optional[str] = Field(None, max_length=100)
    friday: Optional[str] = Field(None, max_length=100)
    saturday: Optional[str] = Field(None, max_length=100)
    sunday: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


class TagCreate(BaseModel):
    """Schema for creating a tag."""
    tag_name: str = Field(..., min_length=1, max_length=50)

    @field_validator("tag_name")
    @classmethod
    def normalise_tag(cls, v: str) -> str:
        return v.strip().lower()


class PlaceUpdate(BaseModel):
    """Schema for updating an existing place (all fields optional)."""
    place_name: Optional[str] = Field(None, min_length=2, max_length=300)
    name_english: Optional[str] = Field(None, max_length=300)
    ai_summary: Optional[str] = Field(None, max_length=5000)
    suggested_duration: Optional[str] = Field(None, max_length=100)
    best_time_to_visit: Optional[str] = Field(None, max_length=200)
    place_tip: Optional[str] = Field(None, max_length=2000)
    advanced_booking: Optional[str] = Field(None, max_length=100)
    sunrise_view: Optional[bool] = None
    sunset_view: Optional[bool] = None
    cost: Optional[Literal["free", "low", "medium", "high"]] = None
    rating_tourist_priority: Optional[int] = Field(None, ge=1, le=5)
    rating_traveler_experience: Optional[int] = Field(None, ge=1, le=5)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)
    official_website: Optional[str] = Field(None, max_length=500)
    rank_score: Optional[float] = Field(None, ge=0.0, le=5.0)


# ---------------------------------------------------------------------------
# Bulk import wrapper
# ---------------------------------------------------------------------------

class PlaceBulkImport(BaseModel):
    """Wrapper for bulk place ingestion."""
    places: List[PlaceCreate] = Field(..., min_length=1, max_length=10000)
    skip_geo_check: bool = False


# ---------------------------------------------------------------------------
# Validation result (returned by dry-run / validate-only)
# ---------------------------------------------------------------------------

class RowError(BaseModel):
    """A single validation error for a row."""
    row: int
    field: Optional[str] = None
    message: str


class GeoWarning(BaseModel):
    """Warning when a place is far from its parent city."""
    row: int
    place_name: str
    distance_km: float
    city_name: str


class ValidationResult(BaseModel):
    """Result of a validation / dry-run pass."""
    total: int = 0
    valid: int = 0
    errors: List[RowError] = Field(default_factory=list)
    warnings: List[GeoWarning] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


class BulkResult(BaseModel):
    """Result of a bulk ingestion operation."""
    inserted: int = 0
    skipped: int = 0
    errors: List[RowError] = Field(default_factory=list)
    warnings: List[GeoWarning] = Field(default_factory=list)
