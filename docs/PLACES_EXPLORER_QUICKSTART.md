# Places Explorer - Quick Start Guide

## 🚀 Start the Application

### Backend (Terminal 1)
```powershell
cd C:\Users\Kashyap\Documents\Deep\Travel\web\backend
python app.py
```
Expected output:
```
* Running on http://127.0.0.1:5000
```

### Frontend (Terminal 2)
```powershell
cd C:\Users\Kashyap\Documents\Deep\Travel\web\frontend
npm run dev
```
Expected output:
```
Local: http://localhost:5173/
```

## 🌐 Access Points

### Main Application
- Homepage: `http://localhost:5173/`
- Places Explorer: `http://localhost:5173/places`

### API Endpoints
- Health Check: `http://localhost:5000/api/places/search`
- Custom City: `http://localhost:5000/api/places/search?city=Tokyo`

## 🧪 Test the Integration

### 1. Visual Test
1. Open `http://localhost:5173/`
2. Scroll to "Features" section
3. Look for "Places Explorer" card with map icon
4. Click "Explore Places →"
5. Should navigate to Places page

### 2. Search Test
1. On Places page, use search bar
2. Type: "zoo" → should filter to zoo-related places
3. Type: "museum" → should show museums
4. Clear search → shows all places

### 3. Backend Connection Test
Open browser console (F12), check Network tab:
- Should see request to: `http://localhost:5000/api/places/search`
- Status should be: `200 OK` (or using mock data if backend unavailable)

### 4. Card Interaction Test
- Hover over place cards (should lift up)
- Click "Visit Website" buttons (opens in new tab)
- Check star ratings display correctly

## 🔍 Troubleshooting

### Backend Not Connecting
**Symptom**: Yellow banner "Using sample data. Backend connection: Failed to fetch places"

**Solution**:
1. Check backend is running: `http://localhost:5000/api/places/search`
2. Check CORS is enabled in `app.py`
3. Verify `.env` file has `GOOGLE_API_KEY`

### No Places Showing
**Symptom**: Empty grid or "No Places Found"

**Check**:
1. Open DevTools Console for errors
2. Verify API response in Network tab
3. Check backend logs for errors

### Images Not Loading
**Symptom**: Gray placeholder images

**Note**: This is expected for mock data. Real API data should have valid image URLs.

### Port Conflicts
**Frontend**: If port 5173 is busy, Vite will suggest an alternative
**Backend**: Change port in `app.py`: `app.run(debug=True, port=5001)`

## 📁 Key Files Reference

### Frontend
```
web/frontend/src/
├── components/
│   ├── page/
│   │   ├── PlacesExplorer.jsx    # Main page
│   │   ├── PlaceCard.jsx         # Card component
│   │   └── HomePage.jsx          # Updated with link
│   ├── css/
│   │   ├── PlacesExplorer.css    # Page styles
│   │   ├── PlaceCard.css         # Card styles
│   │   └── HomePage.css          # Updated styles
│   └── layout/
│       └── Header.jsx            # Has Places link
└── App.jsx                        # Has /places route
```

### Backend
```
web/backend/
├── app.py                         # Has /api/places/search
└── main_engine/
    └── main_engine.py             # Places data source
```

## 🎨 Customization

### Change Default City
In `PlacesExplorer.jsx`, line 35:
```javascript
city = request.args.get('city', 'San Diego')  // Change 'San Diego'
```

### Adjust Number of Places
In `app.py`, line 176:
```python
for place in all_attractions[:20]:  # Change 20 to desired number
```

### Modify Search Behavior
In `PlacesExplorer.jsx`, lines 26-33:
```javascript
const filtered = places.filter(place => {
  // Add custom filters here
});
```

## 📊 Current Features

✅ Search by place name, type, or description
✅ Responsive grid (1-4 columns)
✅ Loading states
✅ Error handling with fallback
✅ Star ratings
✅ External website links
✅ Image error handling
✅ Smooth animations

## 🔜 Coming Soon

- City selector dropdown
- Filter by category/rating
- Map view integration
- Save favorites
- Share places
- Add to trip planner

## 💡 Tips

1. **Performance**: Backend uses caching - first load may be slower
2. **Mock Data**: Available if backend is down (6 sample places)
3. **Search**: Works on name, type, and description
4. **Navigation**: Multiple ways to access (header, homepage, direct URL)

## 🆘 Need Help?

Check these logs:
1. Browser Console (F12 → Console)
2. Backend terminal output
3. Network tab for API calls

Common errors and solutions in `docs/PLACES_EXPLORER_INTEGRATION.md`
