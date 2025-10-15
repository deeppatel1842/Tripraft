# Places UI Data Flow Fix

## Problem
When searching for "pattaya" (which is within the Bangkok hub's 120km radius):
- `main_engine.py` found the cache hit in Bangkok hub
- Reordered places by distance to Pattaya
- BUT did NOT save a separate JSON file for Pattaya
- `app.py` expected a JSON file at `database/adaptive_database/hubs/pattaya.json`
- API returned 500 error because file didn't exist

## Root Cause
The old flow expected every city to have its own JSON file. But with the hub system:
- One hub (e.g., Bangkok) covers a 120km radius
- Queries within that radius (e.g., Pattaya, Hua Hin) reuse the same data
- Data is reordered by distance but not saved to separate files

## Solution
**Removed dependency on JSON files for Places UI**

### Changes Made

#### 1. Added `get_places_for_ui()` function to `main_engine.py`
```python
def get_places_for_ui(user_query_city: str, ...) -> List[Place]:
    """
    Get places data directly for Places UI frontend.
    Returns processed attractions list without saving to JSON file.
    """
```

**What it does:**
- Geocodes the city
- Checks for cache hits in existing hubs
- Recalculates distances relative to queried city (not hub center)
- Re-ranks places based on new distances
- Returns the list directly (no file I/O)

#### 2. Updated `/api/places/search` endpoint in `app.py`

**Old Flow:**
```
User searches → Check for JSON file → If missing, call main_engine → Read JSON → Return
                                      ↓
                                   ERROR (file doesn't exist for hub sub-queries)
```

**New Flow:**
```
User searches → Call get_places_for_ui() → Get data directly → Return
                       ↓
                   Handles everything internally
                   (cache hits, distance calc, ranking)
```

**Code Changes:**
- Removed all file path checking logic
- Removed JSON file reading/writing
- Removed retry mechanisms for file system sync
- Simplified to direct function call

## Benefits

1. **No File System Dependency**: Data flows directly from cache to API to frontend
2. **Works for All Queries**: Hub sub-queries (like Pattaya within Bangkok) work perfectly
3. **Consistent Logic**: Same cache logic for both Places UI and Trip Planner
4. **Better Performance**: No file I/O overhead
5. **Cleaner Code**: Removed complex file handling and retry logic

## Data Flow Now

```
Places UI Frontend
       ↓
   /api/places/search (app.py)
       ↓
   get_places_for_ui() (main_engine.py)
       ↓
   ┌─────────────────────────────┐
   │ Check Central Hub Cache     │
   │ - Bangkok hub exists?       │
   │ - Pattaya within radius?    │
   └─────────────────────────────┘
       ↓ CACHE HIT
   ┌─────────────────────────────┐
   │ Get Bangkok hub attractions │
   │ Recalculate distances to    │
   │ Pattaya (not Bangkok)       │
   │ Re-rank by new distances    │
   └─────────────────────────────┘
       ↓
   Return List[Place] directly
       ↓
   app.py formats for frontend
       ↓
   JSON response to frontend
```

## Testing

Try searching for:
- **Pattaya**: Should return Bangkok hub data, reordered by distance to Pattaya
- **Hua Hin**: Should return Bangkok hub data, reordered by distance to Hua Hin
- **New City**: Should fetch new data and cache it

All should work without creating separate JSON files.

## Notes

- The `main()` function in `main_engine.py` is unchanged (used for CLI/testing)
- `get_places_for_ui()` is a new dedicated function for the Places UI API
- Both share the same core logic (geocoding, caching, ranking)
- JSON files in `hubs/` folder are still created for brand new hubs
- Sub-queries within existing hubs don't need separate files
