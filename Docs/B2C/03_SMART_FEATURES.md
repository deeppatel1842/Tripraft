# Phase 2 -- Smart Features

These are the features that make the app feel smart without needing full AI. They use structured data, public APIs, and rules-based logic to give travelers information they'd otherwise have to Google separately.

---

## Feature Map

```mermaid
graph TD
    A[Smart Features] --> B[Visa Engine]
    A --> C[Weather Intelligence]
    A --> D[Currency Converter]
    A --> E[Travel Alerts]
    A --> F[Time Zone Manager]
    A --> G[Packing Suggestions]
    
    B --> B1[Do I need a visa?]
    B --> B2[How to apply?]
    B --> B3[Processing times]
    
    C --> C1[Best time to visit]
    C --> C2[Current conditions]
    C --> C3[Pack for weather]
    
    D --> D1[Live exchange rates]
    D --> D2[Cost of living comparison]
    D --> D3[Budget in local currency]
    
    E --> E1[Travel advisories]
    E --> E2[Health alerts]
    E --> E3[Event disruptions]
    
    F --> F1[Group spans time zones]
    F --> F2[Meeting scheduler]
    
    G --> G1[Based on destination + weather]
    G --> G2[Activity-specific gear]
```

---

## Visa Engine

This is the most requested feature in travel planning apps, and most competitors don't do it well.

### How It Works

```mermaid
flowchart TD
    A[User's Passport Country] --> B[Visa Engine]
    C[Destination Country] --> B
    D[Trip Duration] --> B
    E[Purpose of Visit] --> B
    
    B --> F{Check Rules Database}
    
    F -->|Visa Free| G["No visa needed<br/>You can stay up to 90 days"]
    F -->|Visa on Arrival| H["Get visa at the airport<br/>Cost: ~$30-50<br/>Bring: passport photo, cash"]
    F -->|eVisa| I["Apply online before you go<br/>Link: [official portal]<br/>Processing: 3-5 business days"]
    F -->|Embassy Visa| J["Visit the embassy<br/>Documents needed: [list]<br/>Processing: 2-4 weeks<br/>Book appointment early"]
    F -->|Transit Visa| K["If transiting through X,<br/>you may need a separate visa"]
```

### Data Sources

| Source | What It Provides | Update Frequency |
|--------|-----------------|------------------|
| Passport Index API | Visa requirements by nationality | Weekly |
| IATA TIMATIC | Airline-verified entry requirements | Real-time |
| Government portals | Official rules, fees, forms | Manual review monthly |
| Sherpa (API) | COVID + visa combined | Real-time |

### Database Design

```mermaid
erDiagram
    VISA_RULE {
        int id PK
        string passport_country
        string destination_country
        string visa_type
        int max_stay_days
        float fee_usd
        string currency
        string apply_url
        int processing_days_min
        int processing_days_max
        string requirements_json
        datetime last_verified
    }
    
    TRANSIT_RULE {
        int id PK
        string transit_country
        string passport_country
        boolean visa_required
        int max_transit_hours
        string notes
    }
```

### User Experience

When a group is planning a trip:
1. Each member sets their passport country in their profile (one time)
2. When a destination is selected, the visa widget automatically shows requirements for each member
3. If someone needs a visa, it shows next steps and timeline
4. The checklist auto-populates with visa tasks ("Apply for eVisa by Dec 15")

---

## Weather Intelligence

### Architecture

```mermaid
flowchart TD
    A[Destination + Dates] --> B{Historical or Real-time?}
    
    B -->|Trip is months away| C[Historical Weather API]
    B -->|Trip is within 14 days| D[Forecast API]
    B -->|Trip is now| E[Current Weather API]
    
    C --> F[Average temps, rainfall,<br/>humidity for those dates<br/>based on 10-year data]
    
    D --> G[14-day forecast<br/>with daily breakdown]
    
    E --> H[Current conditions<br/>+ hourly forecast]
    
    F --> I[Weather Widget in App]
    G --> I
    H --> I
    
    I --> J[Packing suggestions<br/>adjusted for weather]
    I --> K[Activity recommendations<br/>indoor vs outdoor]
    I --> L[Warnings: monsoon season,<br/>extreme heat, etc.]
```

### API Options

| API | Free Tier | Data Quality | Historical Data |
|-----|-----------|-------------|-----------------|
| Open-Meteo | Unlimited | Good | Yes (40+ years) |
| WeatherAPI | 1M calls/mo | Good | Yes |
| Visual Crossing | 1K/day | Excellent | Yes (50+ years) |
| Tomorrow.io | 500/day | Very good | Limited |

**Recommendation**: Open-Meteo for historical + current (free, no API key needed) with WeatherAPI as backup.

### Best Time to Visit

For each destination in our database, pre-compute:

| Month | Avg Temp | Rain Days | Tourist Crowd | Price Level | Score |
|-------|----------|-----------|---------------|-------------|-------|
| Jan | 15C | 8 | Low | $$ | 7/10 |
| Feb | 16C | 6 | Low | $$ | 8/10 |
| ... | ... | ... | ... | ... | ... |
| Jul | 32C | 1 | Very High | $$$$ | 5/10 |

This becomes a powerful planning tool: "Visit in March for the best balance of weather and crowds."

---

## Currency Converter

### Features

```mermaid
flowchart LR
    A[Currency Features] --> B[Live Rates<br/>Updated hourly]
    A --> C[Expense Conversion<br/>Auto-convert in groups]
    A --> D[Cost of Living<br/>Comparison widget]
    A --> E[Budget Planner<br/>In destination currency]
    A --> F[ATM Tips<br/>Best way to get cash]
```

### Cost of Living Comparison

This is the feature that makes people go "oh, nice." Show a side-by-side:

| Item | Home (NYC) | Destination (Bali) | Savings |
|------|-----------|-------------------|---------|
| Meal at restaurant | $25 | $5 | -80% |
| Coffee | $6 | $2 | -67% |
| Hotel night (mid-range) | $200 | $45 | -78% |
| Taxi (5 km) | $15 | $3 | -80% |
| Beer (domestic) | $8 | $2 | -75% |

Data sources: Numbeo API (free tier available), manual verification for popular destinations.

### Multi-Currency Expenses

In the expense engine, when a group is in a foreign country:
- Expenses can be logged in any currency
- Auto-converted to the group's base currency for balances
- Exchange rate at the time of expense is recorded
- Settlement can be in any currency

---

## Travel Alerts

### Alert Types

```mermaid
flowchart TD
    A[Alert Sources] --> B[Government Travel Advisories<br/>Level 1-4 safety ratings]
    A --> C[Health Alerts<br/>Disease outbreaks, vaccinations]
    A --> D[Weather Warnings<br/>Storms, extreme conditions]
    A --> E[Event Disruptions<br/>Strikes, protests, closures]
    A --> F[Entry Requirement Changes<br/>New visa rules, COVID policies]
    
    B --> G[User Notification]
    C --> G
    D --> G
    E --> G
    F --> G
    
    G --> H[In-app banner on trip page]
    G --> I[Push notification if urgent]
    G --> J[Email digest if moderate]
```

### Data Sources

| Source | API Available | Coverage | Reliability |
|--------|-------------|----------|-------------|
| US State Dept | Yes (free) | Global | High (conservative) |
| UK FCDO | Yes (free) | Global | High |
| WHO | RSS feeds | Health | Authoritative |
| GDACS | API | Natural disasters | Real-time |
| Flightradar24 | Paid API | Flight disruptions | Real-time |

### Implementation

For Phase 2, start simple:
1. Store user's upcoming trip destinations
2. Daily cron job checks government advisory APIs
3. If advisory level changes, notify affected users
4. Show advisory banner on trip page

No need to build complex alert routing initially. A daily check with email notification covers 90% of the value.

---

## Time Zone Manager

When a group spans multiple time zones (common for international friend groups):

```mermaid
flowchart TD
    A[Group Members] --> B[Alice: EST -5]
    A --> C[Bob: GMT +0]
    A --> D[Carol: IST +5:30]
    A --> E[Dave: JST +9]
    
    F[Meeting Scheduler] --> G[Find overlapping<br/>reasonable hours]
    G --> H["Best times:<br/>Alice: 8 AM<br/>Bob: 1 PM<br/>Carol: 6:30 PM<br/>Dave: 10 PM"]
    
    I[Trip Itinerary] --> J[Show all times in<br/>destination time zone]
    J --> K[Toggle to see in<br/>your home time zone]
```

### Use Cases
- Planning calls before the trip
- Coordinating arrival times
- "What time is our dinner reservation in my time zone?"

---

## Packing Suggestions

Generated based on:

```mermaid
flowchart TD
    A[Destination] --> E[Packing List Generator]
    B[Weather Forecast] --> E
    C[Trip Duration] --> E
    D[Planned Activities] --> E
    
    E --> F[Essential<br/>Passport, charger, meds]
    E --> G[Weather-specific<br/>Rain jacket, sunscreen]
    E --> H[Activity-specific<br/>Hiking boots, swimsuit]
    E --> I[Cultural<br/>Modest clothing for temples]
    
    F --> J[Auto-added to<br/>group checklist]
    G --> J
    H --> J
    I --> J
```

Rules engine example:
- Destination has temples? Add "modest clothing" 
- Weather shows rain > 5 days? Add "rain jacket, waterproof bag"
- Activity includes hiking? Add "hiking boots, daypack, water bottle"
- Duration > 7 days? Add "laundry bag, travel detergent"
- International trip? Add "power adapter for [country]"

This is rules-based, not AI. Cheaper and just as effective for this use case.

---

## Implementation Priority

| Feature | Effort | User Value | Revenue Impact | Priority |
|---------|--------|-----------|---------------|----------|
| Visa Engine | 3 weeks | Very High | Medium (premium feature) | 1 |
| Weather Intelligence | 2 weeks | High | Low | 2 |
| Currency Converter | 1 week | Medium | Low | 3 |
| Packing Suggestions | 1 week | Medium | Low | 4 |
| Travel Alerts | 2 weeks | High | Medium (premium) | 5 |
| Time Zone Manager | 1 week | Low-Medium | Low | 6 |

### Implementation Order

```mermaid
gantt
    title Smart Features Timeline
    dateFormat YYYY-MM-DD
    
    section High Priority
    Visa Engine        :a1, 2026-06-01, 21d
    Weather Widget     :a2, after a1, 14d
    
    section Medium Priority
    Currency Converter :b1, after a2, 7d
    Packing Engine     :b2, after b1, 7d
    
    section Lower Priority
    Travel Alerts      :c1, after b2, 14d
    Time Zones         :c2, after c1, 7d
```

**Total: ~10-12 weeks** for all smart features. But the visa engine alone (3 weeks) delivers probably 50% of the value.
