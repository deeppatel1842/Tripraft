# Quick Reference - Places Explorer (Fixed)

## ✅ What's Correct Now

### Cache Structure
```
adaptive_database/hubs/
├── san_diego.json      (87 places, 2 airports, ALL data including thumbnailUrl)
├── seattle.json        (ALL data pre-cached)
└── bangkok.json        (ALL data pre-cached)
```

### app.py Logic (Simplified)
```python
# Load cache
all_attractions = json.load(f)

# Filter and use cached data
for place in all_attractions:
    if 'airport' not in place.get('types'):  # Skip airports
        places.append({
            'thumbnailUrl': place.get('thumbnailUrl'),  # ← From cache, NO API call!
            'displayName': place.get('displayName'),
            'rating': place.get('rating'),
            ... all from cache
        })
        if len(places) >= 20:
            break

return jsonify({'places': places})
```

## 🚫 What NOT to Do

### ❌ Don't Make API Calls in app.py
```python
# WRONG - Don't do this!
photo_url = f"https://places.googleapis.com/v1/{photo['name']}/media?key={API_KEY}"
```

### ❌ Don't Include Airports
```python
# WRONG - Don't do this!
for place in all_attractions[:20]:  # Might include airports!
```

## ✅ What to Do

### ✅ Use Cached Data
```python
# CORRECT
thumbnail_url = place.get('thumbnailUrl', '')  # Already in cache!
```

### ✅ Filter Airports
```python
# CORRECT
if 'airport' in place_types:
    continue  # Skip
```

## Data Already Available (No API Needed)

Every cached place has:
- ✅ `thumbnailUrl` (pre-fetched photo URL)
- ✅ `displayName` (name)
- ✅ `rating` (rating)
- ✅ `userRatingCount` (review count)
- ✅ `generativeSummary` (AI summary)
- ✅ `reviewSummary` (review summary)
- ✅ `regularOpeningHours` (opening hours)
- ✅ `websiteUri` (website)
- ✅ `location` (coordinates)
- ✅ `rank_score` (ranking)
- ✅ `distance_to_query` (distance)
- ✅ `types` (place types)

## Quick Test

```bash
# Test cached city
curl "http://localhost:5000/api/places/search?city=San%20Diego"

# Verify:
# 1. Response < 1 second ✓
# 2. 20 places returned ✓
# 3. No "Airport" in names ✓
# 4. All have thumbnailUrl ✓
```

## Console Output (Correct)

```
============================================================
PLACES SEARCH REQUEST
============================================================
City: San Diego
Normalized: san_diego
Hub filename: san_diego
Looking for cache at: .../hubs/san_diego.json
✓ CACHE HIT: Found cached data for 'San Diego'
  Loaded 87 places from cache
✓ Returning 20 places to frontend (airports filtered out)
  Cache Hit: True
============================================================
```

## API Calls

- ✅ main_engine.py: Makes API calls ONCE per city (creates cache)
- ✅ app.py: Makes ZERO API calls (uses cache)

## Cost

- ✅ Cached cities: $0 per request
- ✅ New cities: $0.50 first request, then $0

## Response Time

- ✅ Cached: ~100ms
- ✅ New city: ~20 sec (first time), then ~100ms

## Files to Review

1. **app.py** (lines 232-276) - Uses cached data, filters airports
2. **san_diego.json** - Example cached data with thumbnailUrl
3. **main_engine.py** - Creates cache with all data

## Remember

🎯 **Single Source of Truth**: Cache files have EVERYTHING
🚀 **Zero API Calls**: app.py only reads JSON
🚫 **No Airports**: Filter by type
💰 **Zero Cost**: For cached cities
⚡ **Fast**: ~100ms response

That's it! Simple, efficient, correct. 🎉
