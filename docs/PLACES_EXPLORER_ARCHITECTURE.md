# Places Explorer - Architecture Diagram

## System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                             │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React.js)                               │
│                    Port: 5173                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐         ┌──────────────┐        ┌──────────────┐  │
│  │  HomePage   │────────▶│   Header     │───────▶│  Navigation  │  │
│  │             │         │  (Nav Links) │        │  to /places  │  │
│  └─────────────┘         └──────────────┘        └──────────────┘  │
│        │                                                   │          │
│        │ Feature Card Link                                │          │
│        └─────────────────────────┬─────────────────────────┘          │
│                                  ▼                                    │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              PlacesExplorer.jsx                                 │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │ State Management:                                         │  │ │
│  │  │  - places[]                                               │  │ │
│  │  │  - filteredPlaces[]                                       │  │ │
│  │  │  - searchQuery                                            │  │ │
│  │  │  - loading, error                                         │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  │                                                                  │ │
│  │  ┌──────────────┐                                               │ │
│  │  │ Search Input │───▶ Filter places by name/type/description   │ │
│  │  └──────────────┘                                               │ │
│  │                                                                  │ │
│  │  ┌────────────────────────────────────────────────────────┐    │ │
│  │  │          Places Grid (Responsive 1-4 cols)             │    │ │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │    │ │
│  │  │  │PlaceCard │  │PlaceCard │  │PlaceCard │  ...        │    │ │
│  │  │  └──────────┘  └──────────┘  └──────────┘             │    │ │
│  │  └────────────────────────────────────────────────────────┘    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                  │                                    │
│                                  │ HTTP GET Request                   │
│                                  ▼                                    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    fetch('http://localhost:5000/api/places/search')
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND (Flask/Python)                            │
│                    Port: 5000                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  app.py                                                         │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │  Route: GET /api/places/search?city=<city>              │  │ │
│  │  │                                                           │  │ │
│  │  │  1. Parse city parameter (default: 'San Diego')         │  │ │
│  │  │  2. Import main_engine modules                           │  │ │
│  │  │  3. Load caches (Geocode, Hub, PlaceID)                 │  │ │
│  │  │  4. Get place data                                       │  │ │
│  │  │  5. Format as JSON                                       │  │ │
│  │  │  6. Return top 20 places                                 │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                  │                                    │
│                                  ▼                                    │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  main_engine/main_engine.py                                    │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │  Functions Used:                                          │  │ │
│  │  │  - geocode_city(city)                                     │  │ │
│  │  │  - CentralHubCache.find_matching_hub()                    │  │ │
│  │  │  - CentralHubCache.get_hub_attractions()                  │  │ │
│  │  │  - GeocodeCache.load()                                    │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  │                                                                  │ │
│  │  ┌─────────────────────────────────────────────────────────┐   │ │
│  │  │  Caching Strategy:                                       │   │ │
│  │  │                                                           │   │ │
│  │  │  Level 1: GeocodeCache                                   │   │ │
│  │  │  ├─ City → Coordinates                                   │   │ │
│  │  │  └─ SQLite Database                                      │   │ │
│  │  │                                                           │   │ │
│  │  │  Level 2: CentralHubCache                                │   │ │
│  │  │  ├─ Hub Regions with Attractions                         │   │ │
│  │  │  └─ JSON Files                                           │   │ │
│  │  │                                                           │   │ │
│  │  │  Level 3: PlaceIdCache                                   │   │ │
│  │  │  ├─ Individual Place Details                             │   │ │
│  │  │  └─ JSON Files                                           │   │ │
│  │  └─────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                  │                                    │
│                      ┌───────────┴──────────┐                        │
│                      │  Cache Hit?          │                        │
│                      └───────────┬──────────┘                        │
│                                  │                                    │
│                   ┌──────────────┼──────────────┐                    │
│                   │ YES          │          NO  │                    │
│                   ▼              ▼              ▼                    │
│          ┌──────────────┐  ┌────────────────────────────┐           │
│          │Return Cached │  │  adaptive_quadtree_crawl() │           │
│          │ Attractions  │  │  ┌──────────────────────┐  │           │
│          └──────────────┘  │  │ Google Places API    │  │           │
│                            │  │ Intelligent Crawl    │  │           │
│                            │  │ Store in Cache       │  │           │
│                            │  └──────────────────────┘  │           │
│                            └────────────────────────────┘           │
│                                  │                                    │
│                                  ▼                                    │
│                       ┌────────────────────┐                         │
│                       │  Format Response:  │                         │
│                       │  {                 │                         │
│                       │    success: true,  │                         │
│                       │    city: "...",    │                         │
│                       │    places: [...],  │                         │
│                       │    count: 20       │                         │
│                       │  }                 │                         │
│                       └────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    JSON Response (with CORS headers)
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React.js)                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  PlacesExplorer.jsx receives data                                    │
│                │                                                      │
│                ▼                                                      │
│    ┌────────────────────────┐                                        │
│    │ setPlaces(data.places) │                                        │
│    │ setFilteredPlaces()    │                                        │
│    │ setLoading(false)      │                                        │
│    └────────────────────────┘                                        │
│                │                                                      │
│                ▼                                                      │
│    ┌────────────────────────────────────────────┐                    │
│    │ Render PlaceCard for each place            │                    │
│    │  - Display image                           │                    │
│    │  - Show rating & stars                     │                    │
│    │  - Display description                     │                    │
│    │  - Show types (tags)                       │                    │
│    │  - Add "Visit Website" button             │                    │
│    └────────────────────────────────────────────┘                    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                          USER SEES PLACES


## Component Hierarchy

```
App.jsx
  └─ Routes
      ├─ Route: / → HomePage.jsx
      │   ├─ Header.jsx (with /places link)
      │   ├─ Hero Section
      │   ├─ Features Section
      │   │   └─ Feature Card: "Places Explorer" → Link to /places
      │   └─ Footer.jsx
      │
      └─ Route: /places → PlacesExplorer.jsx
          ├─ Header.jsx (with /places link)
          ├─ Search Input
          ├─ Loading State
          ├─ Error State
          ├─ Places Grid
          │   └─ PlaceCard.jsx (repeated for each place)
          │       ├─ Image
          │       ├─ Rating Badge
          │       ├─ Title
          │       ├─ Description
          │       ├─ Star Rating
          │       ├─ Type Tags
          │       └─ Visit Website Button
          └─ Footer.jsx
```

## Data Flow

```
User Types in Search
      ↓
searchQuery state updates
      ↓
useEffect triggers
      ↓
Filter places array
      ↓
setFilteredPlaces()
      ↓
Re-render PlaceCard components
      ↓
Display filtered results
```

## API Call Flow

```
Component Mounts
      ↓
useEffect(() => fetchPlaces(), [])
      ↓
setLoading(true)
      ↓
fetch('/api/places/search')
      ↓
Backend processes request
      ↓
Check cache
      ↓
Return places data
      ↓
Frontend receives response
      ↓
setPlaces(data.places)
      ↓
setLoading(false)
      ↓
Render cards with animation
```

## Error Handling

```
API Call Failed
      ↓
catch (error)
      ↓
setError(error.message)
      ↓
Load mock data
      ↓
Display warning banner
      ↓
Render with sample data
      ↓
User still sees content
```

## Responsive Layout

```
Mobile (<640px)
├─ 1 column grid
├─ Stacked cards
└─ Full width search

Tablet (640-1024px)
├─ 2 column grid
├─ Side-by-side cards
└─ Centered search

Desktop (1024-1280px)
├─ 3 column grid
├─ Optimal viewing
└─ Wide search bar

Large Desktop (>1280px)
├─ 4 column grid
├─ Maximum density
└─ Full-width layout
```
