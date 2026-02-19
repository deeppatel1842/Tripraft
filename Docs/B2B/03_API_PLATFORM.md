# B2B: API Platform

## What This Is

Expose TripRaft's data and AI capabilities as an API that other developers and businesses can integrate into their own products. If the white-label play is "rent our whole platform," the API play is "rent pieces of it."

---

## What We Can Expose

```mermaid
graph TD
    A[TripRaft API Platform] --> B[Places API]
    A --> C[AI Planning API]
    A --> D[Visa API]
    A --> E[Expense API]
    A --> F[Itinerary API]
    
    B --> B1["Search 16,830+ places<br/>with ratings, photos, coordinates"]
    B --> B2["Autocomplete suggestions"]
    B --> B3["Detailed place info"]
    
    C --> C1["Generate itineraries<br/>from natural language"]
    C --> C2["Destination recommendations<br/>based on preferences"]
    C --> C3["Budget estimation"]
    
    D --> D1["Visa requirements<br/>by passport + destination"]
    D --> D2["Application steps<br/>and timeline"]
    
    E --> E1["Expense splitting<br/>engine as a service"]
    E --> E2["Multi-currency<br/>conversion"]
    
    F --> F1["Itinerary templates<br/>for popular routes"]
    F --> F2["Day-by-day<br/>schedule builder"]
```

---

## Who'd Use This

| Customer | What They'd Use | Why |
|----------|----------------|-----|
| Travel bloggers/influencers | Places API + Itinerary templates | Embed trip plans in their content |
| Other travel apps | Visa API | Don't want to build visa database themselves |
| Event planning platforms | Group expense API | Add expense splitting to their product |
| Corporate tools | AI planning + booking API | Bolt travel onto existing HR tools |
| Chatbot builders | AI planning API | Add trip planning to their bot |
| Content websites | Places API | Dynamic destination content |

---

## API Design

### Authentication

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Portal as API Portal
    participant API as TripRaft API
    
    Dev->>Portal: Sign up, create app
    Portal->>Dev: API key + secret
    
    Dev->>API: Request with API key<br/>X-API-Key: sk_live_abc123
    API->>API: Validate key
    API->>API: Check rate limits
    API->>API: Track usage for billing
    API-->>Dev: Response (JSON)
```

### Endpoints

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| **Places** | /v1/places/search | GET | Search places by keyword, location, category |
| | /v1/places/{id} | GET | Get place details |
| | /v1/places/autocomplete | GET | Typeahead suggestions |
| | /v1/places/nearby | GET | Places near coordinates |
| | /v1/places/popular | GET | Trending destinations |
| **AI** | /v1/ai/itinerary | POST | Generate itinerary from requirements |
| | /v1/ai/recommend | POST | Get personalized recommendations |
| | /v1/ai/chat | POST | Conversational trip planning |
| **Visa** | /v1/visa/check | GET | Requirements for passport→destination |
| | /v1/visa/requirements/{country} | GET | Full entry requirements |
| **Expenses** | /v1/expenses/split | POST | Calculate expense splits |
| | /v1/expenses/simplify | POST | Simplify debts in a group |
| | /v1/currency/convert | GET | Currency conversion |
| **Itinerary** | /v1/itinerary/templates | GET | Pre-built itinerary templates |
| | /v1/itinerary/optimize | POST | Optimize route/schedule |

### Response Format

```json
{
  "status": "success",
  "data": {
    "places": [
      {
        "id": "place_12345",
        "name": "Senso-ji Temple",
        "city": "Tokyo",
        "country": "Japan",
        "category": "temple",
        "rating": 4.7,
        "coordinates": {"lat": 35.7148, "lng": 139.7967},
        "photo_url": "https://cdn.tripraft.com/places/sensoji.jpg",
        "description": "Tokyo's oldest Buddhist temple...",
        "best_time": "Early morning (6-8 AM)",
        "avg_visit_duration": "1-2 hours",
        "admission_fee": "Free"
      }
    ]
  },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 156
  },
  "meta": {
    "request_id": "req_abc123",
    "credits_used": 1,
    "credits_remaining": 4999
  }
}
```

---

## Pricing

### Credit-Based Model

```mermaid
flowchart TD
    A[API Pricing] --> B[Free Tier<br/>1,000 credits/mo]
    A --> C[Developer<br/>$29/mo<br/>10,000 credits]
    A --> D[Business<br/>$99/mo<br/>50,000 credits]
    A --> E[Enterprise<br/>$299/mo<br/>250,000 credits]
    A --> F[Custom<br/>Volume pricing]
    
    subgraph "Credit Costs"
        G["Places search: 1 credit"]
        H["Place detail: 1 credit"]
        I["Visa check: 2 credits"]
        J["AI recommendation: 5 credits"]
        K["AI itinerary: 10 credits"]
        L["AI chat message: 3 credits"]
    end
```

### Why Credits (Not Per-Call)

- AI calls cost us 10-100x more than database lookups
- Credits let us fairly price different endpoints
- Users can self-manage: spend credits on what they need
- Overage charges: $0.005 per credit over limit

### Comparison to Alternatives

| What Api | Their Price | Our Price | Our Advantage |
|----------|-----------|-----------|---------------|
| Google Places API | $32 per 1K calls | ~$3 per 1K calls (places) | 10x cheaper for basic place search |
| Amadeus API | $500/mo min for serious use | $99/mo for 50K credits | More accessible for small apps |
| ChatGPT for travel | Pay per token, build everything | $29/mo for ready-made travel AI | Pre-built, travel-specific |

---

## Developer Portal

```mermaid
flowchart TD

    %% MAIN HUB
    A[Developer Portal]

    A --> B[Documentation]
    A --> C[API Playground]
    A --> D[Dashboard]
    A --> E[SDKs]

    %% DOCUMENTATION
    B --> B1[Getting started guide]
    B --> B2[Full API reference]
    B --> B3[Code examples]
    B --> B4[Use case tutorials]

    %% API PLAYGROUND
    C --> C1[Try endpoints in browser]
    C --> C2[See live responses]
    C --> C3[Generate code snippets]

    %% DASHBOARD
    D --> D1[Usage analytics]
    D --> D2[Billing and invoices]
    D --> D3[API key management]
    D --> D4[Webhook configuration]

    %% SDKS
    E --> E1[Python SDK]
    E --> E2[JavaScript SDK]
    E --> E3[REST any language]

```

### Documentation First

The API is only as good as its documentation. We need:

1. **OpenAPI/Swagger spec** -- auto-generated, interactive
2. **Quick-start guide** -- "Get your first result in 5 minutes"
3. **Language-specific examples** -- Python, JavaScript, cURL
4. **Rate limiting docs** -- What happens when you hit limits
5. **Error reference** -- Every error code explained
6. **Changelog** -- What changed in each API version

---

## Technical Implementation

### Rate Limiting per API Key

```mermaid
flowchart TD
    A[API Request] --> B[Extract API Key]
    B --> C[Redis: Check rate limit]
    C --> D{Within limit?}
    
    D -->|Yes| E[Process request]
    D -->|No| F[429 Too Many Requests<br/>Retry-After header]
    
    E --> G[Redis: Decrement credits]
    G --> H{Credits remaining?}
    H -->|Yes| I[Return response]
    H -->|No credits| J[402 Payment Required<br/>'Upgrade plan or buy credits']
```

| Tier | Requests/min | Concurrent connections | Credits/month |
|------|-------------|----------------------|---------------|
| Free | 30 | 2 | 1,000 |
| Developer | 60 | 5 | 10,000 |
| Business | 120 | 20 | 50,000 |
| Enterprise | 300 | 50 | 250,000 |

### Infrastructure

```mermaid
graph TD
    subgraph "API Gateway"
        A[API Key Auth]
        B[Rate Limiter]
        C[Usage Tracker]
        D[Request Logger]
    end
    
    subgraph "API Services"
        E[Places Service]
        F[AI Service]
        G[Visa Service]
        H[Expense Service]
    end
    
    subgraph "Shared"
        I[PostgreSQL]
        J[Redis]
        K[OpenAI API]
        L[Vector Store]
    end
    
    A --> B --> C --> D
    D --> E --> I
    D --> F --> K
    D --> G --> I
    D --> H --> I
    E --> J
    F --> L
```

The API platform shares the same backend services as the consumer app. The only new components are:
- API key management (new table + middleware)
- Usage tracking and billing (new service)
- Developer portal (new frontend, possibly built with Docusaurus)
- Rate limiting per API key (extend existing rate limiter)

---

## Revenue Projections

| Year | API Customers | Avg MRR/Customer | Monthly Revenue | Annual Revenue |
|------|--------------|------------------|-----------------|---------------|
| 1 | 20 | $50 | $1,000 | $12,000 |
| 2 | 100 | $80 | $8,000 | $96,000 |
| 3 | 300 | $100 | $30,000 | $360,000 |

API revenue is small initially but grows compounding. Each integration is sticky -- once a developer builds on your API, they rarely switch.

---

## Implementation Timeline

```mermaid
gantt
    title API Platform Build
    dateFormat YYYY-MM-DD
    
    section Core
    API key management          :a1, 2027-04-01, 10d
    Rate limiting per key       :a2, after a1, 5d
    Usage tracking + billing    :a3, after a2, 10d
    
    section Endpoints
    Places API                  :b1, after a3, 7d
    Visa API                    :b2, after b1, 5d
    Expense API                 :b3, after b2, 5d
    AI endpoints                :b4, after b3, 14d
    
    section Developer Experience
    OpenAPI spec generation     :c1, after b4, 5d
    Developer portal            :c2, after c1, 14d
    Python + JS SDKs            :c3, after c2, 10d
    
    section Launch
    Beta with 5 developers      :d1, after c3, 21d
    Public launch               :d2, after d1, 7d
```

**Total: approximately 4 months** to public launch.

---

## Long-Term Vision

```mermaid
graph LR
    A[Phase 1:<br/>Basic API] --> B[Phase 2:<br/>AI Endpoints]
    B --> C[Phase 3:<br/>Marketplace]
    C --> D[Phase 4:<br/>Ecosystem]
    
    A --> A1[Places + Visa + Expense]
    B --> B1[AI Itinerary + Chat + Recommendations]
    C --> C1[Third-party plugins<br/>and integrations]
    D --> D1[TripRaft becomes the<br/>data layer for travel tech]
```

The end game: TripRaft's API becomes what Stripe is to payments or Twilio is to communications -- the infrastructure layer that other travel products build on. That's a long way off, but the API platform is how you start.
