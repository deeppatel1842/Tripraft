# Places Explorer - Caching Strategy Documentation

## Overview
The Places Explorer implements an intelligent caching system that checks the adaptive_database first before making API calls to Google Places.

## Caching Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER ENTERS CITY NAME                         │
│                    (e.g., "San Diego")                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               FRONTEND: PlacesExplorer.jsx                       │
│                                                                  │
│  1. User types city name in input field                         │
│  2. Clicks "Search City" button                                 │
│  3. Triggers fetchPlaces(city)                                  │
│                                                                  │
│     fetch('http://localhost:5000/api/places/search?city=...')  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               BACKEND: app.py (/api/places/search)              │
│                                                                  │
│  STEP 1: Normalize City Name                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Input: "San Diego"                                       │  │
│  │  Function: normalize_city_name(city)                      │  │
│  │  Output: "san_diego"                                      │  │
│  │                                                            │  │
│  │  Examples:                                                 │  │
│  │    "New York" → "new_york"                               │  │
│  │    "París" → "paris"                                     │  │
│  │    "São Paulo" → "sao_paulo"                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  STEP 2: Check Cache                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Cache Path:                                              │  │
│  │  main_engine/adaptive_database/hubs/{city}.json          │  │
│  │                                                            │  │
│  │  Example:                                                  │  │
│  │  main_engine/adaptive_database/hubs/san_diego.json       │  │
│  │                                                            │  │
│  │  Check: hub_file_path.exists()                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│                  ┌───────────────────────┐                      │
│                  │   Does Cache Exist?   │                      │
│                  └───────────────────────┘                      │
│                              │                                   │
│              ┌───────────────┴───────────────┐                  │
│              │ YES                       NO  │                  │
│              ▼                               ▼                  │
│  ┌─────────────────────────┐   ┌─────────────────────────────┐ │
│  │ ✓ CACHE HIT             │   │ ✗ CACHE MISS                │ │
│  │                         │   │                             │ │
│  │ Actions:                │   │ Actions:                    │ │
│  │ 1. Load JSON file       │   │ 1. Call main_engine.py      │ │
│  │ 2. Parse places data    │   │ 2. Fetch from Google API   │ │
│  │ 3. Set cache_hit=True   │   │ 3. Save to cache           │ │
│  │ 4. Return immediately   │   │ 4. Load newly cached data  │ │
│  │                         │   │ 5. Set cache_hit=False     │ │
│  │ Speed: ~50ms            │   │ Speed: ~10-30 seconds      │ │
│  │ Cost: $0                │   │ Cost: Google API calls     │ │
│  └─────────────────────────┘   └─────────────────────────────┘ │
│              │                               │                  │
│              └───────────────┬───────────────┘                  │
│                              ▼                                   │
│  STEP 3: Format Response                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  {                                                        │  │
│  │    "success": true,                                       │  │
│  │    "city": "San Diego",                                  │  │
│  │    "places": [...], // Top 20 places                    │  │
│  │    "count": 20,                                           │  │
│  │    "cache_hit": true/false                               │  │
│  │  }                                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               FRONTEND: Display Results                          │
│                                                                  │
│  1. Receive response                                            │
│  2. setPlaces(data.places)                                      │
│  3. setCacheHit(data.cache_hit)                                │
│  4. Display cache status banner:                                │
│     - Green banner: "Loaded from cache (instant!)"             │
│     - Yellow banner: "Fetched fresh from Google Places API"    │
│  5. Render PlaceCard components                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Cache Directory Structure

```
web/backend/main_engine/
├── adaptive_database/
│   ├── central_hub.json          # Master hub registry
│   └── hubs/                     # Cached city data
│       ├── san_diego.json        # ✓ Cached
│       ├── seattle.json          # ✓ Cached
│       ├── bangkok.json          # ✓ Cached
│       └── bangkok_rankings.txt  # Additional data
├── geocode_database/
│   └── geocode_cache.db          # City → Coordinates cache
└── main_engine.py                # Fetch & cache engine
```

## Example Cache File: san_diego.json

```json
[
  {
    "id": "ChIJd-tZsWCq3oAR_sO70namuLg",
    "displayName": {"text": "SeaWorld San Diego"},
    "location": {"latitude": 32.764622, "longitude": -117.226494},
    "types": ["amusement_park", "tourist_attraction"],
    "rating": 4.4,
    "userRatingCount": 45230,
    "websiteUri": "https://seaworld.com/san-diego/",
    "photos": [...],
    "generativeSummary": {
      "overview": {"text": "Ocean park featuring..."}
    },
    "rank_score": 0.8542
  },
  ...more places...
]
```

## User Experience Scenarios

### Scenario 1: First-Time City Search (Cache Miss)

**User Action**: Types "Paris" and clicks "Search City"

**What Happens**:
1. Frontend sends request to backend
2. Backend normalizes: "Paris" → "paris"
3. Checks: `adaptive_database/hubs/paris.json` → NOT FOUND
4. Backend prints: "✗ CACHE MISS: No cached data for 'Paris'"
5. Backend calls `main_engine.py` with "Paris"
6. main_engine.py:
   - Geocodes Paris → lat/lng
   - Searches Google Places API (radius-based)
   - Fetches attraction details
   - Ranks and scores places
   - Saves to `paris.json`
7. Backend loads newly cached data
8. Returns to frontend with `cache_hit: false`
9. Frontend shows **YELLOW BANNER**: "Results for 'Paris' fetched fresh from Google Places API"
10. Displays 20 top places

**Time**: 10-30 seconds
**Cost**: Multiple Google API calls (~$0.20-$0.50)

### Scenario 2: Repeat City Search (Cache Hit)

**User Action**: Types "San Diego" and clicks "Search City"

**What Happens**:
1. Frontend sends request to backend
2. Backend normalizes: "San Diego" → "san_diego"
3. Checks: `adaptive_database/hubs/san_diego.json` → FOUND!
4. Backend prints: "✓ CACHE HIT: Found cached data for 'San Diego'"
5. Backend loads JSON file
6. Returns to frontend with `cache_hit: true`
7. Frontend shows **GREEN BANNER**: "Results for 'San Diego' loaded from cache (instant!)"
8. Displays 20 top places

**Time**: 50-200ms
**Cost**: $0 (no API calls)

### Scenario 3: Filtering Places

**User Action**: After loading San Diego, types "zoo" in filter box

**What Happens**:
1. Frontend filters local `places` array
2. No backend call needed
3. Instantly shows matching places (e.g., San Diego Zoo)

**Time**: Instant (<10ms)
**Cost**: $0

## Backend Console Output

### Cache Hit Example:
```
============================================================
PLACES SEARCH REQUEST
============================================================
City: San Diego
Normalized: san_diego
Hub filename: san_diego
Looking for cache at: C:\...\hubs\san_diego.json
✓ CACHE HIT: Found cached data for 'San Diego'
  Loaded 87 places from cache
✓ Returning 20 places to frontend
  Cache Hit: True
============================================================
```

### Cache Miss Example:
```
============================================================
PLACES SEARCH REQUEST
============================================================
City: Paris
Normalized: paris
Hub filename: paris
Looking for cache at: C:\...\hubs\paris.json
✗ CACHE MISS: No cached data for 'Paris'
  Calling main_engine.py to fetch places...

===== Searching for 'Paris' with travel mode 'DRIVE' =====
Geocoding city: Paris
CACHE HIT (L1): Query falls within the 'paris' hub.
...
✓ Fetched and cached 142 places
✓ Returning 20 places to frontend
  Cache Hit: False
============================================================
```

## Performance Comparison

| Scenario | Cache Status | Response Time | API Calls | Cost |
|----------|-------------|---------------|-----------|------|
| First search for city | MISS | 10-30 sec | 5-15 | $0.20-$0.50 |
| Repeat search | HIT | 50-200 ms | 0 | $0 |
| Filter places | N/A | <10 ms | 0 | $0 |

## Cache Invalidation

Currently, cached data **never expires** automatically. To refresh:

### Manual Refresh:
1. Delete the specific JSON file: `hubs/{city}.json`
2. Search for the city again
3. Fresh data will be fetched and cached

### Programmatic Refresh (Future):
- Add TTL (Time To Live) to cache entries
- Auto-refresh after X days
- Admin endpoint to clear cache

## Benefits of This Caching Strategy

1. **Speed**: Instant results for popular cities
2. **Cost**: Massive savings on API calls
3. **Reliability**: Works offline for cached cities
4. **UX**: Clear feedback (green/yellow banners)
5. **Scalability**: Can pre-cache popular destinations

## Cities Currently Cached

Based on directory listing:
- ✅ San Diego
- ✅ Seattle
- ✅ Bangkok

## How to Pre-Cache Popular Cities

Run from terminal:
```powershell
cd web\backend\main_engine
python main_engine.py "New York"
python main_engine.py "London"
python main_engine.py "Tokyo"
```

This will fetch and cache data for future instant access.

## API Endpoint Usage

### Request:
```http
GET /api/places/search?city=San%20Diego HTTP/1.1
Host: localhost:5000
```

### Response (Cache Hit):
```json
{
  "success": true,
  "city": "San Diego",
  "places": [...],
  "count": 20,
  "cache_hit": true
}
```

### Response (Cache Miss):
```json
{
  "success": true,
  "city": "Paris",
  "places": [...],
  "count": 20,
  "cache_hit": false
}
```

## Error Handling

### Invalid City:
```json
{
  "error": "Failed to fetch places",
  "detail": "Could not geocode city: XYZ"
}
```

### Backend Error:
```json
{
  "error": "Failed to fetch places",
  "detail": "Error details here"
}
```

Frontend falls back to mock data in both cases.

## Future Enhancements

1. **Cache warming**: Pre-fetch top 100 cities
2. **Partial updates**: Update specific places without full refresh
3. **Cache compression**: Reduce JSON file sizes
4. **CDN integration**: Serve cached JSON from CDN
5. **Analytics**: Track cache hit rates
6. **Smart expiration**: Auto-refresh stale data (>30 days)
