# Feature: AI Trip Planner

## Overview

The AI Trip Planner generates personalized day-by-day travel itineraries using external AI agents (Crew AI). Users provide a city, trip duration, pacing preference, and optional tag filters. The system returns a structured itinerary with stops, times, descriptions, and coordinates — rendered on an interactive Leaflet map.

---

## System Flow

```
Browser                     Flask Backend              Crew AI Service
   │                             │                          │
   │  User fills form:           │                          │
   │  - City: "Barcelona"        │                          │
   │  - Days: 5                  │                          │
   │  - Pacing: "Moderate"       │                          │
   │  - Exclude: ["nightlife"]   │                          │
   │  - Require: ["food"]        │                          │
   │                             │                          │
   │  POST /api/v1/              │                          │
   │  trip-planner/generate      │                          │
   │  {city, days, pacing,       │                          │
   │   exclude_tags, require_tags}│                         │
   │────────────────────────────>│                          │
   │                             │                          │
   │                             │  TripGenerateSchema      │
   │                             │  validation              │
   │                             │                          │
   │                             │  Build AI prompt:        │
   │                             │  - City context          │
   │                             │  - Duration + pacing     │
   │                             │  - Tag constraints       │
   │                             │  - Output format spec    │
   │                             │    (structured JSON)     │
   │                             │                          │
   │                             │  POST to Crew AI API     │
   │                             │─────────────────────────>│
   │                             │                          │
   │                             │                          │ AI generates:
   │                             │                          │ - Day breakdown
   │                             │                          │ - Stop details
   │                             │                          │ - Time slots
   │                             │                          │ - Coordinates
   │                             │                          │ - Descriptions
   │                             │                          │
   │                             │  JSON response           │
   │                             │ <────────────────────────│
   │                             │                          │
   │                             │  Parse + validate        │
   │                             │  response structure      │
   │                             │                          │
   │  200 OK                     │                          │
   │  {itinerary: {              │                          │
   │    city: "Barcelona",       │                          │
   │    days: [{                 │                          │
   │      day: 1,                │                          │
   │      title: "Gothic...",    │                          │
   │      stops: [{              │                          │
   │        name: "La Rambla",   │                          │
   │        time: "09:00",       │                          │
   │        duration: "2h",      │                          │
   │        lat: 41.38,          │                          │
   │        lng: 2.17,           │                          │
   │        description: "...",  │                          │
   │        category: "landmark" │                          │
   │      }, ...]                │                          │
   │    }, ...],                 │                          │
   │    tips: [...],             │                          │
   │    checklist: [...]         │                          │
   │  }}                         │                          │
   │ <───────────────────────────│                          │
   │                             │                          │
   │  Frontend renders:          │                          │
   │  1. Itinerary list          │                          │
   │  2. Leaflet map with        │                          │
   │     day-colored markers     │                          │
   │  3. Suggested places        │                          │
   │  4. Packing checklist       │                          │
   │  5. Travel tips             │                          │
```

---

## Components

### Backend

| File | Purpose |
|------|---------|
| `app/api/v1/trips.py` | POST `/trips/generate` — AI trip generation, GET `/trips/cities` and `/trips/search-cities` — city autocomplete |
| `app/services/crew_agent_service.py` | CrewAgentService: process_mention, call_crew_api |
| `app/services/crew_conversation.py` | CrewConversation: stateful multi-turn conversation management |
| `app/services/crew_parsers.py` | Response parsing: markdown to JSON, structured output extraction |
| `app/schemas/trips.py` | TripGenerateSchema: city, days (1-14), pacing, tags |

### Frontend

| File | Purpose |
|------|---------|
| `src/components/pages/jsx/TripPlanner.jsx` | Main page wrapper: manages state, Leaflet loading |
| `src/components/tripPlanner/jsx/TripForm.jsx` | Input form: city, days (1-14), pacing toggle, tag filters |
| `src/components/tripPlanner/jsx/TripMap.jsx` | Leaflet map: day-by-day color-coded markers |
| `src/components/tripPlanner/jsx/Itinerary.jsx` | Day-by-day breakdown with stop list |
| `src/components/tripPlanner/jsx/ItineraryStop.jsx` | Single stop: name, time, category, notes, image |
| `src/components/tripPlanner/jsx/SuggestedPlaces.jsx` | Recommended places carousel for current day |
| `src/components/tripPlanner/jsx/Checklist.jsx` | Interactive packing checklist |
| `src/components/tripPlanner/jsx/TripTips.jsx` | Travel tips panel (weather, visas, local info) |
| `src/components/tripPlanner/jsx/TripPlanCard.jsx` | Compact trip summary card |
| `src/components/tripPlanner/jsx/Icon.jsx` | Activity category icon renderer |
| `src/services/tripPlannerService.js` | API service: POST /trip-planner/generate |
| `src/hooks/useTripPlannerQuery.js` | TanStack Query mutation: useGenerateTrip |

---

## Input Parameters

| Parameter | Type | Validation | Description |
|-----------|------|-----------|-------------|
| `city` | string | Required | Destination city name |
| `days` | integer | 1-14 | Trip duration in days |
| `pacing` | enum | Relaxed / Moderate / Packed | Activity density per day |
| `exclude_tags` | string[] | Optional | Activity types to exclude |
| `require_tags` | string[] | Optional | Activity types to require |

## Pacing Levels

| Level | Stops/Day | Description |
|-------|-----------|-------------|
| Relaxed | 2-3 | Slow mornings, long lunches, early evenings |
| Moderate | 4-5 | Balanced mix of sightseeing and downtime |
| Packed | 6-8 | Dawn to dusk, maximize coverage |

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/trip-planner/generate` | Optional | Generate AI itinerary |
| GET | `/trips/cities` | None | List available cities |
| GET | `/trips/search-cities` | None | City autocomplete |

---

## Map Visualization

The frontend dynamically loads Leaflet from CDN and renders:
- Numbered markers for each stop, color-coded by day
- Polyline connecting stops in chronological order
- Popup with stop name, time, and category on click
- Day legend with color swatches
- Auto-fit bounds to show all markers

Day color palette defined in `src/components/groupPlanner/constants/mapConfig.js`.
