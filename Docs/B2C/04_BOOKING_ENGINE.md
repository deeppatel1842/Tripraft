# Phase 3 -- Booking Engine

This is where TripRaft starts making money through transactions, not just subscriptions. Instead of planning a trip in our app and then leaving to book on Expedia, users book through us. We earn affiliate commissions or referral fees on every transaction.

---

## What We're Building

```mermaid
flowchart TD
    A[User plans trip in TripRaft] --> B{Ready to book}
    
    B --> C[Flights]
    B --> D[Hotels]
    B --> E[Activities & Events]
    
    C --> F[Search flights via Amadeus API]
    F --> G[Show results in our UI]
    G --> H[User selects flight]
    H --> I[Redirect to airline or OTA<br/>with affiliate link]
    I --> J[We earn 1-3% commission]
    
    D --> K[Search hotels via Booking.com API]
    K --> L[Show results in our UI]
    L --> M[User selects hotel]
    M --> N[Book via affiliate or API]
    N --> O[We earn 4-8% commission]
    
    E --> P[Search events via<br/>Ticketmaster / GetYourGuide]
    P --> Q[Show results in our UI]
    Q --> R[User selects activity]
    R --> S[Redirect to provider]
    S --> T[We earn 5-10% commission]
```

---

## Flight Integration

### API Options

| Provider | Type | Free Tier | Data Coverage | Integration Effort |
|----------|------|-----------|--------------|-------------------|
| Amadeus | Direct API | 500 calls/mo | Near-complete (global) | High (complex API) |
| Skyscanner | Affiliate API | Free (revenue share) | Global | Medium |
| Kiwi.com | Affiliate API | Free (revenue share) | Global + virtual interlining | Medium |
| Google Flights | No public API | N/A | N/A | N/A (scraping not viable) |
| Duffel | Direct API | Pay-per-search | Good (growing) | Medium |

**Recommendation**: Start with Skyscanner Affiliate API (free, revenue share model, easier integration), then add Amadeus for deeper control when volume justifies the cost.

### Flight Search Flow

```mermaid
sequenceDiagram
    participant User
    participant FE as React App
    participant API as Our Backend
    participant Cache as Redis
    participant Flight as Skyscanner API

    User->>FE: Search: NYC → Tokyo<br/>Mar 15-22, 4 passengers
    FE->>API: GET /api/v1/flights/search<br/>{origin, dest, dates, passengers}
    
    API->>Cache: Check cache key
    alt Cache hit (within 15 min)
        Cache-->>API: Cached results
        API-->>FE: Results (from cache)
    else Cache miss
        API->>Flight: Search request
        Flight-->>API: Results (airlines, prices, times)
        API->>API: Normalize data format
        API->>API: Attach affiliate links
        API->>Cache: Store (TTL: 15 min)
        API-->>FE: Results
    end
    
    FE->>FE: Display with filters<br/>(price, stops, airline, time)
    User->>FE: Select flight
    FE->>FE: Open affiliate link<br/>in new tab
    
    Note over User, Flight: User completes booking<br/>on airline/OTA site
    Note over API: We earn commission<br/>per completed booking
```

### Revenue per Booking

| Route Type | Avg Booking Value | Commission Rate | Revenue per Booking |
|-----------|------------------|----------------|-------------------|
| Domestic short-haul | $200 | 1-2% | $2-4 |
| International economy | $800 | 1-3% | $8-24 |
| International business | $3,000 | 1-3% | $30-90 |
| Group (4 people) | $3,200 | 1-3% | $32-96 |

The group angle is our advantage. A group of 4 booking together = 4x the commission per search.

---

## Hotel Integration

### API Options

| Provider | Type | Commission | Coverage | Min Volume |
|----------|------|-----------|----------|------------|
| Booking.com Affiliate | Affiliate | 25-40% of their commission (~4-6%) | 28M+ listings | None |
| Hotels.com Affiliate | Affiliate | 4-6% | Large | None |
| Expedia Affiliate (EAN) | API | 4-8% | Very large | Apply |
| Agoda Affiliate | Affiliate | 5-7% | Asia-focused | None |
| Hostelworld | Affiliate | ~5% | Hostels/budget | None |

**Recommendation**: Booking.com Affiliate Program (largest inventory, no minimum volume, decent commission).

### Hotel Search UX

```mermaid
flowchart TD
    A[Trip destination + dates selected] --> B[Auto-search hotels<br/>in background]
    B --> C[Hotel suggestions appear<br/>in trip planning page]
    
    C --> D[Filter By]
    D --> D1[Price range]
    D --> D2[Star rating]
    D --> D3[Distance from itinerary stops]
    D --> D4[Guest rating]
    D --> D5[Amenities]
    
    C --> E[Smart Suggestions]
    E --> E1[Best value based on budget]
    E --> E2[Closest to your activities]
    E --> E3[Highest rated in area]
    
    C --> F[Group Features]
    F --> F1[Rooms needed calculator]
    F --> F2[Total cost split view]
    F --> F3[Vote on hotel options]
```

The key UX insight: don't make users leave the planning page. Hotels appear alongside the itinerary, not on a separate booking page. "You're visiting Shibuya on Day 2 -- here's a hotel 5 minutes away."

---

## Activities & Events

### API Options

| Provider | Type | Commission | Coverage |
|----------|------|-----------|----------|
| GetYourGuide | Affiliate | 8% | 60K+ activities globally |
| Viator (TripAdvisor) | Affiliate | 8% | 300K+ activities |
| Ticketmaster | API | Varies | Events, concerts, sports |
| Klook | Affiliate | 5-8% | Asia-focused |
| Musement | API | 8-10% | Europe tours |

**Recommendation**: GetYourGuide Partner API (good coverage, generous commission, easy integration).

### Activity Suggestions

```mermaid
flowchart TD
    A[User's Itinerary] --> B[Day 1: Tokyo - Shibuya area]
    B --> C[Auto-suggest activities<br/>near Shibuya]
    
    C --> D["Shibuya Crossing Walking Tour<br/>⭐ 4.8 | $35/person | 2 hours"]
    C --> E["Japanese Cooking Class<br/>⭐ 4.9 | $65/person | 3 hours"]
    C --> F["teamLab Borderless Tickets<br/>⭐ 4.7 | $30/person | 2 hours"]
    
    D --> G[Add to itinerary + book]
    E --> G
    F --> G
    
    G --> H[Activity appears in<br/>day plan with time slot]
    H --> I[Group expense auto-created<br/>if booked through us]
```

The magic: booking an activity through TripRaft automatically creates an expense entry in the group's expense tracker. Less manual work.

---

## Integration Architecture

```mermaid
graph TD
    subgraph "Our Backend"
        A[Booking Service Layer]
        B[Flight Adapter]
        C[Hotel Adapter]
        D[Activity Adapter]
        E[Affiliate Link Manager]
        F[Booking Tracker]
    end
    
    subgraph "External APIs"
        G[Skyscanner API]
        H[Booking.com API]
        I[GetYourGuide API]
    end
    
    subgraph "Data Storage"
        J[Search Cache - Redis<br/>TTL: 15-30 min]
        K[Booking Records - PostgreSQL<br/>track affiliate conversions]
        L[Price Alerts - PostgreSQL<br/>track price changes]
    end
    
    A --> B --> G
    A --> C --> H
    A --> D --> I
    A --> E
    A --> F
    
    B --> J
    C --> J
    D --> J
    
    F --> K
    F --> L
```

### Adapter Pattern

Each booking provider gets an adapter that normalizes the data:

```mermaid
classDiagram
    class BookingAdapter {
        <<interface>>
        +search(params) SearchResult[]
        +get_details(id) BookingDetail
        +get_affiliate_link(id) string
    }
    
    class SkyscannerAdapter {
        +search(params) FlightResult[]
        +get_details(id) FlightDetail
        +get_affiliate_link(id) string
    }
    
    class BookingComAdapter {
        +search(params) HotelResult[]
        +get_details(id) HotelDetail
        +get_affiliate_link(id) string
    }
    
    class GetYourGuideAdapter {
        +search(params) ActivityResult[]
        +get_details(id) ActivityDetail
        +get_affiliate_link(id) string
    }
    
    BookingAdapter <|-- SkyscannerAdapter
    BookingAdapter <|-- BookingComAdapter
    BookingAdapter <|-- GetYourGuideAdapter
```

This means we can swap providers without changing frontend code.

---

## Price Alerts

A feature that brings users back to the app:

```mermaid
sequenceDiagram
    participant User
    participant App as TripRaft
    participant Cron as Price Checker
    participant API as Flight/Hotel API
    participant Email as Resend

    User->>App: Set price alert:<br/>"Notify me if NYC-Tokyo<br/>drops below $600"
    App->>App: Store alert in DB

    loop Every 6 hours
        Cron->>API: Check current prices
        API-->>Cron: Current: $580
        Cron->>Cron: $580 < $600 threshold
        Cron->>Email: Send alert
        Email-->>User: "Price dropped to $580!<br/>Book now through TripRaft"
    end
    
    User->>App: Clicks email link
    App->>App: Affiliate booking flow
```

Price alerts drive:
- **Engagement**: Users open the app regularly
- **Conversions**: Urgency drives bookings
- **Revenue**: Each alert-driven booking earns commission

---

## Revenue Projections

### Per-User Revenue (Annual)

| Scenario | Trips/Year | Bookings/Trip | Avg Commission | Annual Revenue/User |
|----------|-----------|---------------|----------------|-------------------|
| Light traveler | 1 | 2 (flight + hotel) | $15 | $30 |
| Regular traveler | 2 | 4 (flights + hotels + activities) | $20 | $160 |
| Frequent traveler | 4 | 6 (full booking per trip) | $25 | $600 |

### Platform Revenue by Scale

| MAU | Active Bookers (10%) | Avg Revenue/Booker | Monthly Revenue | Annual Revenue |
|-----|---------------------|-------------------|----------------|---------------|
| 1,000 | 100 | $15 | $1,500 | $18,000 |
| 10,000 | 1,000 | $15 | $15,000 | $180,000 |
| 50,000 | 5,000 | $18 | $90,000 | $1,080,000 |
| 100,000 | 10,000 | $20 | $200,000 | $2,400,000 |

These are conservative. The group angle means a single "booking decision" often converts 2-6 people at once.

---

## Implementation Timeline

```mermaid
gantt
    title Booking Engine Phases
    dateFormat YYYY-MM-DD
    
    section Flight Search
    Skyscanner API integration    :a1, 2026-09-01, 14d
    Flight search UI              :a2, after a1, 10d
    Affiliate link tracking       :a3, after a2, 5d
    
    section Hotel Search
    Booking.com API integration   :b1, after a3, 14d
    Hotel search + display UI     :b2, after b1, 10d
    Smart hotel suggestions       :b3, after b2, 7d
    
    section Activities
    GetYourGuide integration      :c1, after b3, 10d
    Activity suggestions in itinerary :c2, after c1, 7d
    Auto-expense creation         :c3, after c2, 3d
    
    section Price Alerts
    Alert system backend          :d1, after c3, 7d
    Price check cron job          :d2, after d1, 5d
    Email notifications           :d3, after d2, 3d
```

**Total: approximately 14-16 weeks** for the complete booking engine.
