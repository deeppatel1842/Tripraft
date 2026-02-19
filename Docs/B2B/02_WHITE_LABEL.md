# B2B: White-Label Platform

## The Idea

Instead of only selling TripRaft directly to travelers, license the platform to businesses that want their own branded travel planning tool. They get the technology; we get recurring platform fees.

---

## Who Wants This

```mermaid
graph TD
    A[White-Label Customers] --> B[Travel Agencies]
    A --> C[Tourism Boards]
    A --> D[Hotel Chains]
    A --> E[Airlines]
    A --> F[Destination Marketing Orgs]
    
    B --> B1["Want: branded trip planning for clients<br/>Now: email + PDF itineraries"]
    C --> C1["Want: interactive destination planner<br/>Now: static brochure websites"]
    D --> D1["Want: trip planning around their properties<br/>Now: just a booking page"]
    E --> E1["Want: trip planning after flight booking<br/>Now: 'you booked a flight, now what?'"]
    F --> F1["Want: attract visitors with planning tools<br/>Now: blog posts and Instagram"]
```

### Why They'd Pay Us Instead of Building It

Building a trip planning platform from scratch takes 12-18 months and $500K+ in development costs. We've already built it. They just need their logo on it.

---

## What They Get

```mermaid
flowchart TD
    A[White-Label Package] --> B[Core Platform]
    A --> C[Customization]
    A --> D[Data]
    A --> E[Support]
    
    B --> B1[Trip planning]
    B --> B2[Group collaboration]
    B --> B3[Expense tracking]
    B --> B4[Itinerary builder]
    B --> B5[Voting & polls]
    
    C --> C1[Custom branding<br/>Logo, colors, fonts]
    C --> C2[Custom domain<br/>plan.theirbrand.com]
    C --> C3[Custom place database<br/>Filter to their destinations]
    C --> C4[Custom features<br/>Toggle on/off]
    C --> C5[Custom email templates]
    
    D --> D1[Analytics dashboard<br/>How their users use it]
    D --> D2[Booking data<br/>What's being planned]
    D --> D3[User insights<br/>Demographics, preferences]
    
    E --> E1[Technical onboarding]
    E --> E2[Priority bug fixes]
    E --> E3[Quarterly feature updates]
```

---

## Architecture: Multi-Tenant White-Label

```mermaid
flowchart TD
    subgraph "Single Codebase"
        A[TripRaft Platform]
    end
    
    subgraph "Tenant: Adventure Travel Co"
        B[plan.adventuretravel.com]
        C[Their branding]
        D[Their place database:<br/>Adventure destinations only]
    end
    
    subgraph "Tenant: Visit Portugal"
        E[planner.visitportugal.pt]
        F[Portugal tourism branding]
        G[Their place database:<br/>Portugal destinations only]
    end
    
    subgraph "Tenant: Hilton Hotels"
        H[trips.hilton.com]
        I[Hilton branding]
        J[Their place database:<br/>Cities with Hilton properties]
    end
    
    A --> B
    A --> E
    A --> H
    
    subgraph "Shared Infrastructure"
        K[Same backend code]
        L[Same database<br/>tenant isolation via org_id]
        M[Same Redis cache]
        N[Separate asset storage<br/>per tenant]
    end
```

### Tenant Configuration

Each white-label client gets a configuration record:

```
{
  "tenant_id": "adventure-travel",
  "display_name": "Adventure Trip Planner",
  "domain": "plan.adventuretravel.com",
  "branding": {
    "logo_url": "https://cdn.../logo.png",
    "primary_color": "#FF6B35",
    "secondary_color": "#004E89",
    "font": "Inter"
  },
  "features": {
    "expense_tracking": true,
    "ai_chat": true,
    "booking_engine": false,
    "group_size_limit": 20
  },
  "places_filter": {
    "categories": ["adventure", "hiking", "diving", "climbing"],
    "countries": null  // all countries
  },
  "email_from": "trips@adventuretravel.com"
}
```

The React frontend reads tenant config at load time and applies branding. No code changes needed per tenant.

---

## Use Cases

### 1. Travel Agency

```mermaid
sequenceDiagram
    participant Agent as Travel Agent
    participant WL as White-Label Platform
    participant Client as Client (Traveler)

    Agent->>WL: Create trip plan for client
    Agent->>WL: Add curated places, hotels, activities
    WL->>Client: Email: "Your trip plan is ready!"
    Client->>WL: View itinerary on agency-branded site
    Client->>WL: Share with travel companions
    Client->>Client: Modify preferences, vote
    Client->>Agent: "We love option B, let's book it"
    Agent->>Agent: Books through their systems
    Agent->>WL: Mark trip as confirmed
```

Value for agency: Professional-looking interactive itineraries instead of PDF attachments. Clients spend more time engaging with the plan, leading to more bookings.

### 2. Tourism Board

```mermaid
flowchart TD
    A[Visit Portugal Website] --> B[Plan Your Trip button]
    B --> C[White-labeled TripRaft]
    C --> D[Only shows Portugal destinations]
    C --> E[Curated recommended itineraries]
    C --> F[Built-in booking for<br/>Portuguese hotels and tours]
    
    D --> G[User creates trip plan]
    E --> G
    F --> G
    
    G --> H[Shares with friends<br/>'Let's go to Portugal!']
    H --> I[More visitors to Portugal]
    
    J[Tourism Board Dashboard] --> K[How many trips being planned]
    J --> L[Most popular destinations]
    J --> M[Average trip length]
    J --> N[Conversion: plan → actual visit]
```

Value for tourism board: Interactive engagement tool instead of static content. Data on what tourists actually want to do.

### 3. Hotel Chain

```mermaid
flowchart TD
    A[Guest books Hilton Tokyo] --> B[Post-booking email:<br/>'Plan the rest of your trip']
    B --> C[White-labeled TripRaft<br/>centered on Hilton property]
    
    C --> D[Suggest activities near hotel]
    C --> E[Show restaurants nearby]
    C --> F[Offer upgrades:<br/>spa, airport transfer]
    
    D --> G[Guest builds full trip]
    E --> G
    F --> G
    
    G --> H[Guest more excited<br/>about the stay]
    G --> I[Ancillary revenue<br/>from suggestions]
    G --> J[Longer stays<br/>'One more night for the tour']
```

Value for hotel chain: Increased ancillary revenue and guest engagement. Turns a room booking into a trip experience.

---

## Pricing

### Tiered Model

| Tier | Monthly Fee | Setup Fee | Best For |
|------|-----------|-----------|----------|
| Starter | $499/mo | $1,000 | Small agencies (< 100 trips/mo) |
| Growth | $1,499/mo | $2,500 | Mid-size agencies, small tourism boards |
| Enterprise | $4,999/mo | $10,000 | Large brands, hotel chains, national tourism |
| Custom | Negotiated | Negotiated | Airlines, major hospitality groups |

### What Each Tier Gets

| Feature | Starter | Growth | Enterprise |
|---------|---------|--------|-----------|
| Custom branding | Logo + colors | Full theme | Complete custom |
| Custom domain | Subdomain only | Custom domain | Multiple domains |
| Place database | Global (our data) | Filtered + custom | Full custom import |
| AI features | Basic chat | Full AI | Custom AI persona |
| User limit | 500/mo | 5,000/mo | Unlimited |
| Analytics | Basic | Advanced | Full + API access |
| Support | Email | Email + chat | Dedicated account manager |
| API access | No | Limited | Full |
| SLA | 99.5% | 99.9% | 99.95% |

### Revenue Potential

| Scenario | Clients | Avg MRR/Client | Total MRR | Annual |
|----------|---------|----------------|-----------|--------|
| Year 1 | 5 | $1,000 | $5,000 | $60,000 |
| Year 2 | 20 | $1,500 | $30,000 | $360,000 |
| Year 3 | 50 | $2,000 | $100,000 | $1,200,000 |

White-label is a slow-build revenue stream. Each client takes time to onboard, but once they're live, churn is extremely low (switching costs are high).

---

## Technical Implementation

### What Needs to Change

```mermaid
flowchart TD
    A[Current: Single-Tenant] --> B[Target: Multi-Tenant]
    
    B --> C[Database: Add org_id<br/>to every table]
    B --> D[Frontend: Dynamic branding<br/>from tenant config]
    B --> E[Auth: Org-scoped sessions]
    B --> F[API: Tenant middleware<br/>filter all queries by org]
    B --> G[Asset storage:<br/>Per-tenant S3 buckets]
    B --> H[Email: Per-tenant<br/>sender addresses]
    B --> I[DNS: Wildcard or<br/>per-tenant custom domains]
```

### Multi-Tenancy Strategy

Two options:

| Strategy | How | Pros | Cons |
|----------|-----|------|------|
| Shared database + org_id column | Single DB, all tenants | Simpler, cheaper | Risk of data leak, noisy neighbor |
| Database per tenant | Separate DB per client | Full isolation, easy backup | More infrastructure, more cost |

**Recommendation**: Start with shared database + strict org_id filtering. Move to per-tenant databases for enterprise clients who require it.

### Implementation Timeline

```mermaid
gantt
    title White-Label Build
    dateFormat YYYY-MM-DD
    
    section Multi-Tenancy
    Org model + tenant config     :a1, 2027-01-01, 14d
    Tenant middleware              :a2, after a1, 7d
    Org-scoped auth               :a3, after a2, 7d
    
    section Branding
    Dynamic theme engine          :b1, after a3, 10d
    Custom domain routing         :b2, after b1, 7d
    Tenant asset management       :b3, after b2, 5d
    
    section Admin
    Tenant admin dashboard        :c1, after b3, 14d
    Analytics per tenant          :c2, after c1, 10d
    Billing integration           :c3, after c2, 7d
    
    section Launch
    Beta with 2 agencies          :d1, after c3, 30d
    Public availability           :d2, after d1, 14d
```

**Total: approximately 4-5 months** from start to public launch.
