# Phase 2 -- AI Integration

This is where TripRaft stops being "a travel planning tool with group features" and becomes "an AI travel agent that happens to have a great group experience." The difference matters for positioning, retention, and eventually revenue.

---

## The Vision

```mermaid
graph TD
    A[User says: 'Plan a 5-day trip to<br/>Japan for 4 friends who<br/>love food and hiking'] --> B[AI Agent]
    
    B --> C[Understand preferences]
    B --> D[Search our place database]
    B --> E[Check budget constraints]
    B --> F[Consider travel logistics]
    B --> G[Factor in weather/seasons]
    
    C --> H[Generate Draft Itinerary]
    D --> H
    E --> H
    F --> H
    G --> H
    
    H --> I[Day 1: Arrive Tokyo,<br/>Tsukiji morning, Shibuya afternoon]
    H --> J[Day 2: Day trip to Hakone,<br/>hiking + hot springs]
    H --> K[Day 3-5: Kyoto,<br/>temples + food tour]
    
    I --> L[Group votes on it]
    J --> L
    K --> L
    L --> M[Refine based on feedback]
    M --> N[Final itinerary]
```

---

## Architecture: Agentic AI

We're not just wrapping ChatGPT. We're building an agentic system where the AI has tools it can call, memory of past interactions, and the ability to reason through multi-step plans.

```mermaid
flowchart TD
    A[User Input] --> B[Orchestrator Agent]
    
    B --> C{What does the user need?}
    
    C -->|Plan a trip| D[Planning Agent]
    C -->|Find places| E[Search Agent]
    C -->|Budget help| F[Budget Agent]
    C -->|Logistics| G[Logistics Agent]
    C -->|General question| H[Knowledge Agent]
    
    D --> I[Our Place DB<br/>16,830 places]
    D --> J[External APIs<br/>Google, Amadeus]
    D --> K[User Preferences<br/>Past trips, votes]
    
    E --> I
    E --> J
    
    F --> L[Price Data]
    F --> M[Budget Templates]
    
    G --> N[Visa Requirements]
    G --> O[Flight Routes]
    G --> P[Weather Data]
    
    D --> Q[Generated Itinerary]
    E --> R[Place Recommendations]
    F --> S[Budget Breakdown]
    G --> T[Logistics Checklist]
    H --> U[Answered Question]
```

### Agent Types

| Agent | Responsibility | Tools Available | LLM |
|-------|---------------|----------------|-----|
| Orchestrator | Route requests, maintain conversation | All sub-agents | GPT-4o (reasoning) |
| Planning | Generate itineraries | Place DB, APIs, budget | GPT-4o |
| Search | Find places matching criteria | Place DB, Google Places | GPT-4o-mini (cheaper) |
| Budget | Cost estimation and optimization | Price data, templates | GPT-4o-mini |
| Logistics | Visa, weather, transport | Government APIs, weather API | GPT-4o-mini |
| Knowledge | Answer travel questions | RAG over travel knowledge base | GPT-4o-mini |

### Why Agentic (Not Just a Chat Wrapper)

```mermaid
sequenceDiagram
    participant User
    participant Orch as Orchestrator
    participant Plan as Planning Agent
    participant Search as Search Agent
    participant Budget as Budget Agent

    User->>Orch: "Plan a week in Italy for<br/>4 people, budget $3000 total"
    
    Orch->>Orch: Parse intent: trip planning<br/>Extract: Italy, 7 days, 4 people, $3000
    
    Orch->>Search: Find top cities in Italy<br/>for groups, mix of food + culture
    Search->>Search: Query our DB + rank
    Search-->>Orch: Rome, Florence, Amalfi Coast, Venice

    Orch->>Budget: $3000 / 4 people / 7 days<br/>What's feasible?
    Budget->>Budget: $107/person/day<br/>Mid-range budget
    Budget-->>Orch: Can do 2-3 cities,<br/>hostels or budget hotels,<br/>local restaurants

    Orch->>Plan: Build itinerary:<br/>Italy, 7 days, 2-3 cities,<br/>mid-range, food + culture focus
    Plan->>Plan: Day-by-day generation<br/>with logistics between cities
    Plan-->>Orch: Draft itinerary with<br/>estimated costs per day

    Orch-->>User: "Here's what I'd suggest:<br/>[Full itinerary with budget]<br/>Want me to adjust anything?"
```

A simple chat wrapper would give you a generic itinerary. Our agentic system:
- Uses our own data (16,830 real places with ratings)
- Respects budget constraints mathematically
- Accounts for travel time between locations
- Remembers group preferences from past trips
- Can be asked to modify ("swap day 3, we don't like museums")

---

## LLM Strategy

### Model Selection

| Use Case | Model | Cost per 1M tokens | Why |
|----------|-------|--------------------|----|
| Complex reasoning | GPT-4o | ~$5 input / $15 output | Best at multi-step planning |
| Simple tasks | GPT-4o-mini | ~$0.15 input / $0.60 output | 90% cheaper, good enough |
| Embeddings | text-embedding-3-small | $0.02 | For semantic search |
| Fallback | Claude 3.5 Sonnet | ~$3 input / $15 output | If OpenAI is down |

### Cost Control

```mermaid
flowchart TD
    A[User Request] --> B{Complexity?}
    
    B -->|Simple: 'best restaurants in Paris'| C[GPT-4o-mini<br/>~$0.001 per query]
    B -->|Complex: 'Plan my 2-week honeymoon'| D[GPT-4o<br/>~$0.05 per query]
    
    C --> E{In cache?}
    D --> E
    
    E -->|Yes| F[Return cached result<br/>$0]
    E -->|No| G[Call LLM]
    
    G --> H[Cache result<br/>TTL: 1-24 hours]
    H --> I[Return to user]
```

Key cost-saving strategies:
1. **Semantic caching**: Similar questions get cached answers (embedding similarity > 0.95)
2. **Model routing**: Simple questions go to cheaper models
3. **Token budgets**: Each user tier gets monthly token limits
4. **Streaming**: Stream responses so users see progress (better UX, same cost)
5. **Prompt optimization**: Shorter, more efficient prompts without sacrificing quality

### Estimated AI Costs per User

| User Type | Queries/Month | Avg Cost/Query | Monthly AI Cost |
|-----------|---------------|----------------|-----------------|
| Casual | 5-10 | $0.005 | $0.03-0.05 |
| Active | 20-40 | $0.01 | $0.20-0.40 |
| Power | 80-100 | $0.02 | $1.60-2.00 |

At 10,000 MAU with typical distribution: **~$500-800/month in AI costs.**

---

## Implementation Phases

### Phase 2A: Basic AI Chat (4-6 weeks)

```mermaid
flowchart TD
    A[Build Chat UI] --> B[Connect to OpenAI API]
    B --> C[System prompt with<br/>TripRaft context]
    C --> D[RAG over our place DB]
    D --> E[User can ask questions<br/>about destinations]
```

What this gives us:
- "What are the best beaches in Thailand?"
- "Compare Bali vs. Phuket for a group of 6"
- "What's the best time to visit Japan?"

Backend integration:
- New `/api/v1/ai/chat` endpoint
- Conversation history stored in DB
- Place database indexed with embeddings for RAG
- Rate limited per user tier

### Phase 2B: Smart Recommendations (4-6 weeks)

```mermaid
flowchart TD
    A[User Profile] --> B[Preference Engine]
    C[Past Trips] --> B
    D[Voting History] --> B
    E[Saved Places] --> B
    
    B --> F[User Taste Vector]
    
    F --> G[Rank all places<br/>by affinity score]
    G --> H["You might like:<br/>1. Kyoto (98% match)<br/>2. Prague (95% match)<br/>3. Cartagena (92% match)"]
```

What this gives us:
- Personalized place recommendations
- "You liked X, you'll love Y"
- Group compatibility scoring ("3 of 4 members would enjoy this")
- Smart defaults in the planning flow

### Phase 2C: AI Itinerary Generation (6-8 weeks)

```mermaid
flowchart TD
    A[User: 'Plan my trip'] --> B[Collect requirements]
    B --> C[Destination, dates, group size,<br/>budget, interests, pace]
    C --> D[AI generates itinerary]
    D --> E[Day-by-day plan with:<br/>- Places from our DB<br/>- Time estimates<br/>- Travel between stops<br/>- Meal suggestions<br/>- Cost estimates]
    E --> F[User reviews]
    F --> G{Happy?}
    G -->|No| H[Modify: 'More museums,<br/>less shopping']
    H --> D
    G -->|Yes| I[Save to group itinerary]
    I --> J[Share with group for voting]
```

This is the flagship feature. The one that makes people say "wow" and share the app.

---

## Data Pipeline for AI

```mermaid
flowchart TD
    A[Our Place Database<br/>16,830 places] --> B[Generate Embeddings<br/>text-embedding-3-small]
    B --> C[Vector Store<br/>Pinecone or pgvector]
    
    D[External Sources] --> E[Travel guides]
    D --> F[TripAdvisor reviews summary]
    D --> G[Wikipedia extracts]
    E --> H[Process & Embed]
    F --> H
    G --> H
    H --> C
    
    I[User Query] --> J[Generate Query Embedding]
    J --> K[Similarity Search in Vector Store]
    K --> L[Top 10 relevant chunks]
    L --> M[Feed to LLM with context]
    M --> N[Grounded, accurate response]
```

### Why RAG Matters

Without RAG, the AI hallucinates. It'll recommend restaurants that closed 3 years ago or hotels that don't exist. By grounding responses in our verified database, we get:

- Accurate place data (ratings, photos, coordinates)
- Links to real places in our app
- Consistent quality (our data is curated)
- No hallucinated businesses

---

## Group AI Features

| Feature | Description | Phase |
|---------|------------|-------|
| Group taste profile | Merge individual preferences into group consensus | 2B |
| Conflict detection | "Alice wants beaches but Bob wants mountains" | 2B |
| Compromise suggestions | "Here's a place with both: Cinque Terre" | 2B |
| Smart poll generation | AI suggests what to vote on based on disagreements | 2C |
| Budget optimizer | "If you drop day 4 in Paris, you can afford an extra day in Rome" | 2C |
| Re-planning | "It's going to rain Tuesday, here are indoor alternatives" | 3 |

---

## Technical Requirements

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM API | OpenAI API (primary) | Text generation |
| Vector DB | pgvector (PostgreSQL extension) | Semantic search |
| Embeddings | text-embedding-3-small | Convert text to vectors |
| Prompt management | LangChain or custom | Template management, chain-of-thought |
| Streaming | Server-Sent Events (SSE) | Real-time response streaming |
| Conversation store | PostgreSQL table | Chat history per user/group |
| Token counter | tiktoken library | Track usage for billing |

### Infrastructure Additions

```mermaid
graph TD
    subgraph "New Components for AI"
        A[OpenAI API<br/>via API key]
        B[pgvector extension<br/>on existing PostgreSQL]
        C[Embedding pipeline<br/>batch job]
        D[SSE endpoint<br/>/api/v1/ai/chat/stream]
        E[Token usage tracker<br/>per user, per month]
    end
    
    subgraph "Existing (unchanged)"
        F[Flask API]
        G[PostgreSQL]
        H[Redis Cache]
        I[React Frontend]
    end
    
    I --> D
    D --> F
    F --> A
    F --> B
    B --> G
    F --> H
    C --> G
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| AI costs spiral | Burn money fast | Token budgets, model routing, caching |
| Hallucinations | Users get wrong info | RAG grounding, fact-checking layer |
| OpenAI downtime | AI features unavailable | Fallback to Claude, graceful degradation |
| Slow responses | Bad UX | Streaming, async generation, progress indicators |
| Prompt injection | Users manipulate AI | Input sanitization, system prompt hardening |
| Data privacy | User data in LLM context | No PII in prompts, anonymize before sending |

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Chat engagement | 40% of active users try AI chat | PostHog events |
| Itinerary adoption | 25% of trips use AI-generated plans | DB query |
| Recommendation click-through | 15% CTR on suggestions | Frontend tracking |
| AI cost per user | < $0.50/month average | Token usage logs |
| Response time (streaming start) | < 2 seconds | API monitoring |
| User satisfaction with AI | > 4.0/5 rating | In-app feedback |
