# Data Structure Mapping: Backend to Frontend

## Overview
This document explains how the trip planner data is transformed from the backend format to the frontend display format.

## Backend Data Structure (from `advanced_trip.py`)

### Itinerary Format
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
      "theme": "Exploring Historic Downtown",
      "activities": [
        {
          "place_name": "Gaslamp Quarter",
          "start_time": "09:00",
          "opening_hours": "24 Hours",
          "visit_duration_mins": 180,
          "place_obj": {
            "id": "place_id",
            "displayName": {"text": "Gaslamp Quarter"},
            "types": ["tourist_attraction", "neighborhood"],
            "location": {"latitude": 32.711, "longitude": -117.162},
            "rating": 4.5,
            "userRatingCount": 5000
          },
          "cluster_id": 1,
          "needs_lunch_break": false,
          "website": "https://example.com",
          "travel_time_to_next": "~7 minutes"
        }
      ]
    }
  ],
  "other_top_places": [
    {
      "name": "Balboa Park",
      "rating": 4.8,
      "review_count": 77051,
      "types": ["park", "tourist_attraction"]
    }
  ]
}
```

## Frontend Expected Structure

### Itinerary Format (Used by UI Components)
```javascript
{
  title: "SAN DIEGO EXPLORER",
  airport: {
    name: "San Diego International Airport",
    distance_km: 5.2
  },
  itinerary: [
    {
      day: 1,
      title: "Exploring Historic Downtown",
      stops: [
        {
          arrivalTime: "09:00",
          name: "Gaslamp Quarter",
          icon: "mapPin",
          color: "text-purple-600",
          hours: "24 Hours",
          visitDuration: "~180 minutes",
          travelToNext: "~7 minutes",
          lunch: false,
          endOfDay: false,
          coords: [32.711, -117.162],
          website: "https://example.com"
        }
      ]
    }
  ],
  highRankedPlaces: [
    {
      name: "Balboa Park",
      rating: 4.8,
      reviewCount: 77051
    }
  ]
}
```

## Transformation Logic

### 1. Top Level
- `data.city` → `title` (uppercased + " EXPLORER")
- `data.airport` → `airport` (direct copy)
- `data.itinerary` → `itinerary` (transformed)
- `data.other_top_places` → `highRankedPlaces` (transformed)

### 2. Itinerary Transformation
For each day in `data.itinerary`:
- `day.day` → `day` (direct copy)
- `day.theme` → `title` (or "Day X" if theme is empty)
- `day.activities` → `stops` (array mapping)

### 3. Activity to Stop Transformation
For each activity in `day.activities`:
- `activity.start_time` → `arrivalTime`
- `activity.place_name` → `name`
- `activity.place_obj.types` → `icon` (via icon mapping function)
- Fixed value → `color` ("text-purple-600")
- `activity.opening_hours` → `hours`
- `activity.visit_duration_mins` → `visitDuration` (formatted as "~X minutes")
- `activity.travel_time_to_next` → `travelToNext`
- `activity.needs_lunch_break` → `lunch`
- Last stop flag → `endOfDay` (true for last stop)
- `activity.place_obj.location` → `coords` (array: [lat, lng])
- `activity.website` → `website`

### 4. Icon Mapping Function
Maps place types to icon names:
```javascript
const iconMap = {
  'restaurant', 'cafe' → 'utensils'
  'museum', 'art_gallery' → 'museum'
  'park', 'natural_feature' → 'leaf'
  'shopping_mall', 'store' → 'shoppingBag'
  'beach' → 'sun'
  'amusement_park' → 'star'
  'aquarium', 'zoo' → 'fish'
  'night_club', 'bar' → 'moon'
  'airport' → 'plane'
  'church', 'place_of_worship' → 'landmark'
  default → 'mapPin'
}
```

### 5. Other Top Places Transformation
For each place in `data.other_top_places`:
- `place.name` → `name`
- `place.rating` → `rating`
- `place.review_count` → `reviewCount` (default 0 if missing)

## Key Differences

| Backend Field | Frontend Field | Transformation |
|---------------|----------------|----------------|
| `theme` | `title` | Direct copy or "Day X" fallback |
| `activities` | `stops` | Array mapping with field transformations |
| `start_time` | `arrivalTime` | Direct copy |
| `place_name` | `name` | Direct copy |
| `visit_duration_mins` | `visitDuration` | Format: "~X minutes" |
| `travel_time_to_next` | `travelToNext` | Direct copy (may be null) |
| `needs_lunch_break` | `lunch` | Direct copy (boolean) |
| `place_obj.types` | `icon` | Map types to icon name |
| `review_count` | `reviewCount` | Rename field |

## Component Dependencies

### Components That Use This Data:

1. **TripPlanCard.jsx**
   - Expects: `plan.title`, `plan.airport`, `plan.itinerary`, `plan.highRankedPlaces`
   - Renders: Airport info, itinerary list, suggested places

2. **Itinerary.jsx**
   - Expects: `itinerary` array with `day`, `title`, `stops`
   - Renders: Daily schedule with all stops

3. **ItineraryStop.jsx**
   - Expects: `stop` object with all stop properties
   - Renders: Individual stop details (time, name, icon, duration, etc.)

4. **HighRankedPlaces.jsx**
   - Expects: `places` array with `name`, `rating`, `reviewCount`
   - Renders: List of recommended places not in itinerary

5. **TripMap.jsx**
   - Expects: `plans` array, each with `itinerary` containing `stops` with `coords`
   - Renders: Interactive map with route visualization

## Error Prevention

### Null/Undefined Checks:
```javascript
// Safe array access
(day.activities || []).map(...)
(data.other_top_places || []).map(...)

// Safe object access
activity.place_obj?.location

// Default values
reviewCount: place.review_count || 0
travelToNext: activity.travel_time_to_next || null
```

### Data Validation:
- Always check if arrays exist before mapping
- Provide default values for optional fields
- Handle missing location data gracefully
- Mark last stop as `endOfDay`

## Testing Checklist

- [ ] Airport info displays correctly
- [ ] Day titles show theme or fallback
- [ ] All stops render with correct icons
- [ ] Visit duration formatted properly
- [ ] Travel times between stops show
- [ ] Lunch breaks indicated
- [ ] End of day markers appear
- [ ] Map shows route with coordinates
- [ ] Suggested places list renders
- [ ] No undefined/null errors in console

## Future Enhancements

1. **Multiple Plans**: Transform array of plans instead of single plan
2. **Travel Mode Icons**: Add car/walk/transit icons based on distance
3. **Price Estimates**: Include cost information if available
4. **Photos**: Add place photos from backend
5. **Reviews**: Include sample reviews or highlights
6. **Weather**: Integrate weather data for each day
