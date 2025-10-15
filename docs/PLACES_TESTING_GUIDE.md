# Places Explorer - Testing Guide

## Quick Test Steps

### 1. Start Backend
```powershell
cd C:\Users\Kashyap\Documents\Deep\Travel\web\backend
python app.py
```

Expected output:
```
* Running on http://127.0.0.1:5000
* Debug mode: on
```

### 2. Start Frontend
```powershell
cd C:\Users\Kashyap\Documents\Deep\Travel\web\frontend
npm run dev
```

Expected output:
```
Local: http://localhost:5173/
```

### 3. Test Cache Hit (San Diego - Already Cached)

1. Open `http://localhost:5173/places`
2. Type **"San Diego"** in city search
3. Click **"Search City"**
4. Observe:
   - **GREEN banner** appears: "Results for 'San Diego' loaded from cache (instant!)"
   - Places load in **<1 second**
   - 20 places displayed

Backend console should show:
```
✓ CACHE HIT: Found cached data for 'San Diego'
  Loaded 87 places from cache
```

### 4. Test Cache Miss (Paris - Not Cached)

1. Clear the input
2. Type **"Paris"** in city search
3. Click **"Search City"**
4. Observe:
   - Loading spinner appears
   - Takes **10-30 seconds**
   - **YELLOW banner** appears: "Results for 'Paris' fetched fresh from Google Places API"
   - 20 places displayed

Backend console should show:
```
✗ CACHE MISS: No cached data for 'Paris'
  Calling main_engine.py to fetch places...
===== Searching for 'Paris' with travel mode 'DRIVE' =====
...
✓ Fetched and cached 142 places
```

### 5. Test Cache Hit Again (Paris - Now Cached)

1. Type **"Paris"** again
2. Click **"Search City"**
3. Observe:
   - **GREEN banner** this time!
   - Loads instantly
   - Same 20 places

Backend console should show:
```
✓ CACHE HIT: Found cached data for 'Paris'
  Loaded 142 places from cache
```

### 6. Test Filtering

1. After loading any city, type **"museum"** in the filter box
2. Observe:
   - Places filter instantly (no backend call)
   - Only museums shown
3. Clear filter → all places return

### 7. Test Different Cities

Try these searches to test the caching:

**Already Cached** (instant):
- San Diego
- Seattle  
- Bangkok

**Need Fetching** (10-30 sec first time):
- New York
- London
- Tokyo
- Sydney
- Rome

## Expected Behavior Summary

| City Status | First Search | Second Search |
|-------------|--------------|---------------|
| San Diego (cached) | ~100ms, GREEN | ~100ms, GREEN |
| Paris (not cached) | ~20sec, YELLOW | ~100ms, GREEN |
| Tokyo (not cached) | ~20sec, YELLOW | ~100ms, GREEN |

## Verifying Cache Files

After searching for a city, check if it was cached:

```powershell
cd web\backend\main_engine\adaptive_database\hubs
dir
```

You should see:
```
bangkok.json
san_diego.json
seattle.json
paris.json         # ← New after searching Paris
```

View cached data:
```powershell
type paris.json
```

## Testing Checklist

- [ ] Backend starts without errors
- [ ] Frontend loads at localhost:5173/places
- [ ] City search input works
- [ ] Search button triggers fetch
- [ ] Cache HIT shows green banner
- [ ] Cache MISS shows yellow banner
- [ ] Loading spinner appears during fetch
- [ ] Places display in grid
- [ ] Filter search works
- [ ] Place cards have images
- [ ] Star ratings display correctly
- [ ] "Visit Website" buttons work
- [ ] Mobile responsive layout
- [ ] No console errors

## Troubleshooting

### Issue: "City parameter is required" error
**Solution**: Make sure you type a city name before clicking search

### Issue: Backend not connecting
**Solution**: 
1. Check backend is running: `http://localhost:5000/api/places/search?city=test`
2. Check CORS is enabled
3. Verify `.env` has `GOOGLE_API_KEY`

### Issue: Cache miss every time
**Solution**: Check if files are being created in `adaptive_database/hubs/`

### Issue: No images showing
**Solution**: This is expected for some places without photos

### Issue: Takes very long time (>60 sec)
**Solution**: This can happen for large cities. Be patient on first fetch.

## Performance Benchmarks

On a typical system:

**Cache Hit**:
- Backend processing: 10-50ms
- Network transfer: 20-50ms
- Frontend rendering: 50-100ms
- **Total: 100-200ms**

**Cache Miss**:
- Geocoding: 200-500ms
- Places API calls: 10-25 seconds
- Data processing: 1-3 seconds
- Cache save: 100-300ms
- **Total: 10-30 seconds**

## Next Steps

After successful testing:

1. Pre-cache popular cities
2. Add more cities to cache
3. Implement cache refresh mechanism
4. Add pagination for >20 places
5. Add map view
6. Integrate with trip planner
