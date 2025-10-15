# Trip Planner Backend Integration

## Overview
Successfully connected the Trip Planner frontend to the backend API, enabling real trip generation with actual data from the main engine.

## Changes Made

### 1. Frontend API Integration (`TripPlanner.jsx`)

#### Updated `handleGenerate` Function
- Changed from mock data generation to real API calls
- Connects to `http://localhost:5000/api/trip/generate`
- Sends proper request format:
  ```javascript
  {
    city: "San Diego",
    num_days: 3,
    pacing: "M",
    exclude_types: ["museum"],
    require_places: ["Balboa Park"]
  }
  ```

#### Features:
- **Async/Await**: Proper async handling of API requests
- **Error Handling**: Catches and displays errors to users
- **Loading States**: Shows generating status during API call
- **Data Parsing**: Parses comma-separated exclude and require fields
- **Response Formatting**: Transforms backend data to match UI structure

### 2. Airport Information Display (`TripPlanCard.jsx`)

#### New Airport Info Section
- Shows nearest airport name
- Displays distance from city center in kilometers
- Appears at the top of each trip plan card
- Only renders if airport data is available

#### UI Structure:
```jsx
{plan.airport && (
  <div className="airport-info">
    <i className="fas fa-plane-arrival"></i>
    <div className="airport-details">
      <strong>Nearest Airport:</strong> {plan.airport.name}
      <span>({plan.airport.distance_km} km from city center)</span>
    </div>
  </div>
)}
```

### 3. Styling (`TripPlanner.css`)

#### Airport Info Styles
- **Background**: Purple-pink gradient with transparency
- **Border**: Light purple border matching theme
- **Icon**: Large plane icon in purple
- **Layout**: Flexbox with proper spacing
- **Typography**: Clear hierarchy with bold airport name
- **Responsive**: Adapts to different screen sizes

## Backend API Endpoint

### Route: `/api/trip/generate`
**Method:** POST

#### Request Body:
```json
{
  "city": "San Diego",
  "num_days": 3,
  "pacing": "M",
  "exclude_types": ["museum", "park"],
  "require_types": ["beach"],
  "require_places": ["Balboa Park"]
}
```

#### Response Format:
```json
{
  "success": true,
  "city": "San Diego",
  "num_days": 3,
  "pacing": "M",
  "airport": {
    "name": "San Diego International Airport",
    "distance_km": 5.2
  },
  "itinerary": [
    {
      "day": 1,
      "title": "A Day of History & Landmarks",
      "stops": [...]
    }
  ],
  "other_top_places": [...]
}
```

## Data Flow

1. **User Input** → Form fields (city, days, pacing, filters)
2. **Frontend Processing** → Parse and format data
3. **API Request** → POST to `/api/trip/generate`
4. **Backend Processing**:
   - Check for cached data in hub files
   - If not cached, fetch from Google Places API
   - Generate itinerary using algorithms
   - Find nearest airport
   - Return formatted response
5. **Frontend Display** → Show itinerary with airport info

## Key Features

### Airport Integration
- **Automatic Detection**: Backend finds nearest airport to city center
- **Distance Calculation**: Uses haversine formula for accurate distance
- **Visual Prominence**: Purple-themed info box at top of plan
- **User Benefit**: Helps users know where to fly into

### Real-time Generation
- **Loading Indicators**: Shows progress during generation
- **Error Messages**: Clear feedback if something goes wrong
- **No Mock Data**: All trips generated from real place data

### Data Persistence
- **Hub Files**: Backend caches place data in `database/adaptive_database/hubs/`
- **Faster Subsequent Requests**: No need to refetch from Google Places
- **File Format**: JSON files named `{city_name}.json`

## Testing

### Test the Integration:
1. Start the backend server:
   ```bash
   cd web/backend
   python app.py
   ```

2. Start the frontend:
   ```bash
   cd web/frontend
   npm run dev
   ```

3. Navigate to Trip Planner page
4. Enter a city name (e.g., "San Diego")
5. Select number of days and pacing
6. Click "Generate Plan"
7. Verify:
   - Loading state appears
   - Airport info displays at top
   - Itinerary shows actual places
   - Map displays route

### Example Cities to Test:
- San Diego (has cached data)
- New York
- Tokyo
- Paris
- London

## Error Handling

### Frontend Errors:
- Network failures → Alert with error message
- Invalid response → Shows "Invalid response from server"
- Empty results → Backend returns 400 with message

### Backend Errors:
- City not found → 404 error with message
- Invalid parameters → 400 error
- Server error → 500 error with detail

## Future Enhancements

1. **Multiple Plans**: Generate alternative itineraries
2. **Save Plans**: Allow users to save favorite plans
3. **Share Plans**: Generate shareable links
4. **PDF Export**: Download itinerary as PDF
5. **Real-time Updates**: WebSocket for live generation progress
6. **Map Integration**: Show route on interactive map
7. **Weather Integration**: Add weather forecasts for travel dates
8. **Price Estimates**: Show estimated costs for activities

## Notes

- Backend must be running on `localhost:5000`
- CORS is enabled in backend for local development
- Airport data comes from Google Places API with type 'airport'
- Itinerary structure maintained from original mock data format
- All styles use purple/pink theme matching home page

## Files Modified

1. `web/frontend/src/components/page/TripPlanner.jsx` - API integration
2. `web/frontend/src/components/tripPlanner/TripPlanCard.jsx` - Airport display
3. `web/frontend/src/components/css/TripPlanner.css` - Airport styling
4. `web/backend/app.py` - API endpoint (already existed)

## Color Theme

**Purple-Pink Gradient:**
- Primary: `#a855f7` (purple)
- Secondary: `#ec4899` (pink)
- Used for: buttons, links, airport info, active states
