# TripRaft Places Database - Cloud Upload Implementation Plan

## Overview

This document outlines the complete plan to prepare, validate, and upload the places dataset to Firestore, along with API enhancements for city/state search, country overview, and geospatial nearby queries with intelligent caching.

---

## 1. CURRENT STATE ANALYSIS

### Dataset Structure
- **Location**: `web/backend/dataset/countries/`
- **Countries**: 84 country folders
- **Schema**: JSON files per state/city within each country

### Current JSON Schema (varies by file)
```json
{
  "country": "Argentina",
  "state": "San Carlos de Bariloche (Patagonia)",
  "cities": [
    {
      "city": "San Carlos de Bariloche (Patagonia)",
      "nearest_airport": { "name": "...", "iata": "BRC", "city": "..." },
      "places": [
        {
          "name": "Cerro Catedral Ski Resort",
          "ai_summary": "...",
          "name_english": "Catedral Hill Ski Resort",
          "sunrise_view": true,
          "sunset_view": true,
          "sunrise_time": "From high points",
          "sunset_time": "From high points",
          "cost": "Paid (Lift tickets)",
          "rating_tourist_priority": 5,
          "rating_traveler_experience": 5,
          "opening_hours": { "Monday": "...", ... },
          "suggested_duration": "Half-day to Full-day",
          "best_time_to_visit": "Jun–Oct (Skiing)",
          "place_tip": "Book ski passes in advance",
          "advanced_booking": "Recommended",
          "coordinates": { "latitude": -41.1683, "longitude": -71.4397 },
          "address": "...",
          "official_website": "https://...",
          "tags": ["Ski Resort", "Skiing", "Mountain"],
          "photos": { "wikimedia_commons": { ... } },
          "rank_score": 0.819
        }
      ]
    }
  ]
}
```

### Identified Issues
1. **Inconsistent `nearest_airport`** - Some are strings, some are objects
2. **Missing coordinates** - Some places have `null` lat/lng
3. **Invalid photos** - Commons-logo.svg and Airplane_silhouette.svg placeholders
4. **Inconsistent field names** - `latitude/longitude` vs `lat/lng`
5. **Missing `rank_score`** - Some files not yet processed
6. **Missing `state` field** on individual places

---

## 2. TARGET FIRESTORE SCHEMA

### Collection: `places`
Each place is a document with a unique ID.

```json
{
  "id": "argentina_bariloche_cerro_catedral",
  "name": "Cerro Catedral Ski Resort",
  "name_english": "Catedral Hill Ski Resort",
  "name_native": "Cerro Catedral",
  "ai_summary": "Largest ski resort in the Southern Hemisphere...",
  
  "country": "Argentina",
  "country_normalized": "argentina",
  "state": "Patagonia",
  "state_normalized": "patagonia",
  "city": "San Carlos de Bariloche",
  "city_normalized": "san_carlos_de_bariloche",
  
  "coordinates": GeoPoint(-41.1683, -71.4397),
  "has_coordinates": true,
  "address": "Cerro Catedral Base, San Carlos de Bariloche...",
  
  "cost": "Paid",
  "cost_normalized": "paid",
  "rating_tourist_priority": 5.0,
  "rating_traveler_experience": 5.0,
  "rank_score": 0.819,
  
  "opening_hours": {
    "Monday": "Varies seasonally",
    "Tuesday": "Varies seasonally",
    ...
    "notes": "Check official website"
  },
  
  "suggested_duration": "Half-day to Full-day",
  "best_time_to_visit": "Jun–Oct (Skiing)",
  "place_tip": "Book ski passes in advance",
  "advanced_booking": "Recommended",
  "official_website": "https://www.catedralaltapatagonia.com/",
  
  "sunrise_view": true,
  "sunset_view": true,
  "sunrise_time": "From high points",
  "sunset_time": "From high points",
  
  "tags": ["Ski Resort", "Skiing", "Mountain", "Nature"],
  "tags_lowercase": ["ski resort", "skiing", "mountain", "nature"],
  
  "photos": {
    "thumbnail_url": "https://upload.wikimedia.org/...",
    "thumbnail_width": 800,
    "thumbnail_height": 531,
    "attribution": {
      "title": "Cerro Catedral",
      "author": "John Doe",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0",
      "source_url": "https://commons.wikimedia.org/wiki/File:..."
    },
    "has_valid_photo": true
  },
  
  "search_text": "cerro catedral ski resort catedral hill skiing snowboarding patagonia argentina...",
  
  "created_at": Timestamp,
  "updated_at": Timestamp
}
```

### Collection: `cities`
```json
{
  "id": "argentina_san_carlos_de_bariloche",
  "name": "San Carlos de Bariloche",
  "name_normalized": "san_carlos_de_bariloche",
  "country": "Argentina",
  "country_normalized": "argentina",
  "state": "Patagonia",
  "state_normalized": "patagonia",
  
  "nearest_airport": {
    "name": "San Carlos de Bariloche Airport",
    "iata": "BRC",
    "city": "San Carlos de Bariloche"
  },
  
  "place_count": 25,
  "top_places": [
    { "id": "...", "name": "...", "rank_score": 0.819 },
    ...
  ],
  
  "coordinates": GeoPoint(-41.1335, -71.3103),
  "has_coordinates": true,
  
  "created_at": Timestamp,
  "updated_at": Timestamp
}
```

### Collection: `countries`
```json
{
  "id": "argentina",
  "name": "Argentina",
  "name_normalized": "argentina",
  
  "states": [
    {
      "id": "argentina_patagonia",
      "name": "Patagonia",
      "city_count": 5,
      "place_count": 45,
      "top_places": [
        { "id": "...", "name": "...", "rank_score": 0.819, "city": "Bariloche" }
      ]
    }
  ],
  
  "city_count": 10,
  "place_count": 150,
  
  "created_at": Timestamp,
  "updated_at": Timestamp
}
```

### Collection: `search_index` (for autocomplete)
```json
{
  "term": "bariloche",
  "type": "city",
  "display": "San Carlos de Bariloche, Argentina",
  "target_id": "argentina_san_carlos_de_bariloche",
  "country": "Argentina",
  "score": 45
}
```

---

## 3. FIRESTORE INDEXES

Add to `firestore.indexes.json`:

```json
{
  "indexes": [
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "country_normalized", "order": "ASCENDING" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "city_normalized", "order": "ASCENDING" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "state_normalized", "order": "ASCENDING" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "has_coordinates", "order": "ASCENDING" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "places",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "tags_lowercase", "arrayConfig": "CONTAINS" },
        { "fieldPath": "rank_score", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "cities",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "country_normalized", "order": "ASCENDING" },
        { "fieldPath": "place_count", "order": "DESCENDING" }
      ]
    }
  ]
}
```

---

## 4. DATA PIPELINE SCRIPTS

### Script 1: `prepare_dataset.py`

Validates and prepares all JSON files for upload.

**Features:**
- Validate JSON schema for all files
- Generate unique place IDs: `{country}_{city}_{place_name}`
- Normalize field names (latitude→lat, etc.)
- Add missing fields with defaults
- Filter invalid photos (Commons-logo.svg, Airplane_silhouette.svg)
- Generate `search_text` for full-text search
- Create normalized versions of country/city/state
- Generate validation report

**Invalid Photo URLs to filter:**
```python
INVALID_PHOTO_PATTERNS = [
    'Commons-logo.svg',
    'Airplane_silhouette.svg',
    'Flag_of_',
    'Coat_of_arms_of_',
    'Logo_',
    'Icon-',
    'Placeholder',
]
```

### Script 2: `upload_to_firestore.py`

Uploads prepared data to Firestore.

**Features:**
- Batch uploads (500 docs at a time)
- Progress tracking with ETA
- Error handling & retry logic
- Duplicate detection
- Dry-run mode
- Create `places`, `cities`, `countries` collections
- Build aggregation data (place counts, top places)

### Script 3: `validate_photos.py`

Validates and fixes photo URLs.

**Features:**
- Check if photo URL is valid (not placeholder)
- Verify URL returns 200 status
- Set `has_valid_photo: false` for invalid URLs
- Generate report of places needing photos

### Script 4: `sync_dataset.py`

Continuous sync from dataset folder to Firestore.

**Features:**
- Watch dataset folder for changes
- Auto-upload changed files
- Validate before sync
- Logging and notifications

---

## 5. API ENHANCEMENTS

### New Endpoints

#### 1. Search by City/State Name → Get 20 Places
```
GET /api/v1/places/location?q=seattle&limit=20
GET /api/v1/places/location?q=british%20columbia&limit=20
```

**Response:**
```json
{
  "success": true,
  "query": "seattle",
  "match_type": "city",
  "matched": {
    "city": "Seattle",
    "state": "Washington",
    "country": "USA"
  },
  "count": 20,
  "places": [/* top 20 places by rank_score */],
  "cache_hit": false,
  "cache_ttl": 14400,
  "response_time_ms": 145
}
```

**Logic:**
1. Normalize query: lowercase, remove special chars
2. Search cities collection for exact/fuzzy match
3. If no city found, search states collection
4. Return top 20 places by `rank_score`
5. Cache for 4 hours

#### 2. Search by Country → Get States with Top 5 Places Each
```
GET /api/v1/places/country/argentina
```

**Response:**
```json
{
  "success": true,
  "country": "Argentina",
  "state_count": 10,
  "total_places": 150,
  "states": [
    {
      "state": "Patagonia",
      "place_count": 45,
      "top_places": [
        { "id": "...", "name": "Cerro Catedral", "rank_score": 0.819, "city": "Bariloche", "thumbnail_url": "..." },
        { "id": "...", "name": "Civic Center", "rank_score": 0.807, "city": "Bariloche", "thumbnail_url": "..." },
        ...
      ]
    },
    ...
  ],
  "cache_hit": false,
  "cache_ttl": 86400,
  "response_time_ms": 200
}
```

#### 3. Nearby Search with Fallback Location Name
```
GET /api/v1/places/nearby?lat=47.6769&lng=-122.2060&radius=10000&limit=20
```

**Response (when searching from Kirkland, falls back to Seattle data):**
```json
{
  "success": true,
  "search_point": {
    "latitude": 47.6769,
    "longitude": -122.2060
  },
  "search_radius_km": 10,
  "location_name": "Kirkland",
  "data_source": {
    "city": "Seattle",
    "reason": "No places in Kirkland, showing nearest city (Seattle, 12km away)"
  },
  "count": 20,
  "places": [/* places from Seattle sorted by distance */],
  "cache_hit": false,
  "cache_ttl": 3600,
  "response_time_ms": 250
}
```

**Logic:**
1. Search places within radius using bounding box + Haversine
2. If results < 5, expand search to nearest city with data
3. Return places with distance from search point
4. Include `data_source` explaining where data comes from

#### 4. Autocomplete Search
```
GET /api/v1/autocomplete?q=bari&limit=10
```

**Response:**
```json
{
  "success": true,
  "query": "bari",
  "suggestions": [
    { "type": "city", "name": "San Carlos de Bariloche", "country": "Argentina", "place_count": 25 },
    { "type": "city", "name": "Bari", "country": "Italy", "place_count": 15 },
    { "type": "place", "name": "Bariloche Civic Center", "city": "Bariloche", "country": "Argentina" }
  ],
  "cache_hit": true,
  "cache_ttl": 3600
}
```

---

## 6. CACHING STRATEGY

### Cache Keys and TTLs

| Query Type | Cache Key Pattern | TTL | Reason |
|------------|------------------|-----|--------|
| City/State Search | `places:location:{normalized_query}` | 4 hours | User searches same city multiple times |
| Country Overview | `places:country:{country}` | 24 hours | Country data rarely changes |
| Nearby Search | `places:nearby:{lat4}:{lng4}:{radius}` | 1 hour | Location-specific, moderate TTL |
| Place Detail | `places:detail:{place_id}` | 24 hours | Individual place rarely changes |
| Autocomplete | `places:autocomplete:{query}` | 1 hour | Frequently accessed |
| Popular Places | `places:popular:{country}` | 1 hour | Moderately dynamic |

### Cache Implementation

```python
class PlacesCache:
    """Enhanced Redis cache for places API"""
    
    TTL_LOCATION_SEARCH = 14400   # 4 hours
    TTL_COUNTRY_OVERVIEW = 86400  # 24 hours
    TTL_NEARBY_SEARCH = 3600      # 1 hour
    TTL_PLACE_DETAIL = 86400      # 24 hours
    TTL_AUTOCOMPLETE = 3600       # 1 hour
    TTL_POPULAR = 3600            # 1 hour
    
    def get_location_cache_key(self, query: str) -> str:
        normalized = self._normalize_query(query)
        return f"places:location:{normalized}"
    
    def get_nearby_cache_key(self, lat: float, lng: float, radius: int) -> str:
        # Round to 4 decimal places (~11m precision)
        return f"places:nearby:{round(lat, 4)}:{round(lng, 4)}:{radius}"
    
    def get_country_cache_key(self, country: str) -> str:
        return f"places:country:{country.lower()}"
```

### Cache Warming Strategy

On startup or via cron job:
1. Pre-cache all countries overview
2. Pre-cache top 50 most searched cities
3. Pre-cache popular places for top 20 countries

---

## 7. PHOTO VALIDATION

### Invalid Photo Detection

```python
INVALID_PHOTO_PATTERNS = [
    'Commons-logo.svg',
    'Airplane_silhouette.svg',
    'Flag_of_',
    'Coat_of_arms_',
    'Logo_',
    'Icon-',
    'Placeholder',
    'No_image_available',
    'Question_book',
    'Ambox_',
    'Edit-clear',
    'Crystal_Clear',
]

def is_valid_photo_url(url: str) -> bool:
    """Check if photo URL is valid and not a placeholder"""
    if not url:
        return False
    
    url_lower = url.lower()
    for pattern in INVALID_PHOTO_PATTERNS:
        if pattern.lower() in url_lower:
            return False
    
    return True

def sanitize_photos(photos: dict) -> dict:
    """Sanitize photo object, set null for invalid URLs"""
    if not photos:
        return {"thumbnail_url": None, "has_valid_photo": False}
    
    wikimedia = photos.get("wikimedia_commons", {})
    thumbnail = wikimedia.get("thumbnail", {})
    url = thumbnail.get("url")
    
    if not is_valid_photo_url(url):
        return {
            "thumbnail_url": None,
            "has_valid_photo": False,
            "original_url": url,  # Keep for debugging
            "invalid_reason": "placeholder_image"
        }
    
    return {
        "thumbnail_url": url,
        "thumbnail_width": thumbnail.get("width"),
        "thumbnail_height": thumbnail.get("height"),
        "attribution": thumbnail.get("attribution"),
        "has_valid_photo": True
    }
```

---

## 8. GEOSPATIAL NEARBY SEARCH ENHANCEMENT

### Problem Statement
User searches from Kirkland (47.6769, -122.2060) but dataset only has Seattle data.

### Solution
```python
def get_nearby_places_with_fallback(
    self,
    latitude: float,
    longitude: float,
    radius_meters: float = 10000,
    limit: int = 20
) -> Dict:
    """Get nearby places with fallback to nearest city"""
    
    # Step 1: Try direct geospatial search
    places = self._search_places_by_location(latitude, longitude, radius_meters)
    
    if len(places) >= 5:
        return self._format_nearby_response(
            places, latitude, longitude, radius_meters
        )
    
    # Step 2: Find nearest city with data
    nearest_city = self._find_nearest_city_with_data(latitude, longitude)
    
    if not nearest_city:
        return {"success": False, "error": "No places found nearby"}
    
    # Step 3: Get places from nearest city
    city_places = self._get_places_by_city(nearest_city["name"])
    
    # Calculate distance from search point to each place
    for place in city_places:
        if place.get("coordinates"):
            place["distance_m"] = self._haversine_distance(
                latitude, longitude,
                place["coordinates"]["latitude"],
                place["coordinates"]["longitude"]
            )
        else:
            place["distance_m"] = nearest_city["distance_m"]
    
    # Sort by distance
    city_places.sort(key=lambda p: p.get("distance_m", float("inf")))
    
    # Get location name from reverse geocoding (optional)
    search_location_name = self._reverse_geocode(latitude, longitude)
    
    return {
        "success": True,
        "search_point": {"latitude": latitude, "longitude": longitude},
        "search_radius_km": round(radius_meters / 1000, 2),
        "location_name": search_location_name or "Unknown",
        "data_source": {
            "city": nearest_city["name"],
            "country": nearest_city["country"],
            "distance_km": round(nearest_city["distance_m"] / 1000, 1),
            "reason": f"Showing places from {nearest_city['name']} ({round(nearest_city['distance_m']/1000, 1)}km away)"
        },
        "count": min(len(city_places), limit),
        "places": city_places[:limit]
    }
```

---

## 9. IMPLEMENTATION PHASES

### Phase 1: Data Preparation (2-3 days)
- [ ] Create `prepare_dataset.py` script
- [ ] Validate all 84 country datasets
- [ ] Fix inconsistent schemas
- [ ] Generate place IDs
- [ ] Filter invalid photos
- [ ] Generate validation report

### Phase 2: Firestore Upload (1-2 days)
- [ ] Create `upload_to_firestore.py` script
- [ ] Test upload with 1 country (dry run)
- [ ] Upload all countries (batch processing)
- [ ] Create composite indexes
- [ ] Verify data integrity

### Phase 3: API Enhancement (2-3 days)
- [ ] Add `/location` endpoint (city/state search)
- [ ] Add `/country/:name` endpoint (country overview)
- [ ] Enhance `/nearby` with fallback logic
- [ ] Add `/autocomplete` endpoint
- [ ] Update caching with new TTLs

### Phase 4: Photo Validation (1 day)
- [ ] Create `validate_photos.py` script
- [ ] Run validation on all places
- [ ] Generate report of places needing photos
- [ ] Update places with `has_valid_photo` flag

### Phase 5: Testing & Optimization (1-2 days)
- [ ] Write API tests for all endpoints
- [ ] Load test with 100 concurrent users
- [ ] Optimize slow queries
- [ ] Configure cache warming

---

## 10. FILE STRUCTURE

```
web/backend/
├── scripts/
│   └── places_pipeline/
│       ├── prepare_dataset.py      # Validate & prepare data
│       ├── upload_to_firestore.py  # Upload to Firestore
│       ├── validate_photos.py      # Photo validation
│       ├── sync_dataset.py         # Continuous sync
│       └── config.py               # Pipeline configuration
│
├── services/
│   └── places_service.py           # Enhanced service (update)
│
├── api/
│   └── places_routes.py            # Enhanced routes (update)
│
├── cache/
│   ├── redis_client.py             # Existing
│   └── places_cache.py             # New - places-specific caching
│
└── dataset/
    └── countries/                   # Existing dataset
```

---

## 11. COST ESTIMATION

### Firebase Firestore Usage

**Assumptions:**
- 5,000+ places across 84 countries
- 10,000 daily active users
- Average 10 searches per user
- 95% cache hit rate

**Monthly Costs:**

| Operation | Daily Volume | After Cache | Monthly Cost |
|-----------|-------------|-------------|--------------|
| Reads | 100,000 | 5,000 | ~$1.80 |
| Writes | 100 | 100 | ~$0.18 |
| Storage | 100MB | - | FREE |
| **Total** | - | - | **~$2/month** |

### Redis Cache

- Local development: FREE
- Production (Redis Cloud free tier): FREE (30MB)
- Production (if needed): $5-10/month

---

## 12. NEXT STEPS

1. **Review this plan** - Confirm approach
2. **Create scripts** - Build the 4 pipeline scripts
3. **Test with sample** - Upload 1 country, verify API
4. **Full upload** - Process all 84 countries
5. **Enhance API** - Add new endpoints
6. **Deploy** - Production deployment

---

## APPENDIX: Sample API Responses

### City Search Response
```json
GET /api/v1/places/location?q=bariloche

{
  "success": true,
  "query": "bariloche",
  "match_type": "city",
  "matched": {
    "city": "San Carlos de Bariloche",
    "state": "Patagonia",
    "country": "Argentina"
  },
  "count": 20,
  "places": [
    {
      "id": "argentina_bariloche_cerro_catedral",
      "name": "Cerro Catedral Ski Resort",
      "ai_summary": "Largest ski resort in the Southern Hemisphere...",
      "rank_score": 0.819,
      "rating_tourist_priority": 5,
      "rating_traveler_experience": 5,
      "cost": "Paid",
      "coordinates": { "latitude": -41.1683, "longitude": -71.4397 },
      "tags": ["Ski Resort", "Mountain", "Nature"],
      "photos": {
        "thumbnail_url": "https://upload.wikimedia.org/...",
        "has_valid_photo": true
      }
    }
  ],
  "cache_hit": false,
  "cache_ttl": 14400,
  "response_time_ms": 145
}
```

### Country Overview Response
```json
GET /api/v1/places/country/argentina

{
  "success": true,
  "country": "Argentina",
  "state_count": 10,
  "total_places": 150,
  "states": [
    {
      "state": "Patagonia",
      "place_count": 45,
      "top_places": [
        {
          "id": "argentina_bariloche_cerro_catedral",
          "name": "Cerro Catedral Ski Resort",
          "rank_score": 0.819,
          "city": "San Carlos de Bariloche",
          "thumbnail_url": "https://..."
        },
        {
          "id": "argentina_bariloche_civic_center",
          "name": "Civic Center & Lake Nahuel Huapi",
          "rank_score": 0.807,
          "city": "San Carlos de Bariloche",
          "thumbnail_url": null
        }
      ]
    }
  ],
  "cache_hit": false,
  "cache_ttl": 86400,
  "response_time_ms": 200
}
```
