# Feature: AI Agents (Scout and Crew)

## Overview

TripRaft integrates two AI agents into the group chat experience. Users trigger them via `@scout` or `@crew` mentions in group messages. Both agents are consent-gated: a group must opt-in before AI features activate.

- **Scout Agent** — Local LLM (Ollama) for place recommendations and travel suggestions
- **Crew Agent** — External AI service for trip logistics, itinerary modifications, and actionable group operations

---

## Consent Flow

```
User types "@scout" in chat         Flask Backend              Database
     │                                    │                       │
     │  POST /gp/groups/{id}/chat         │                       │
     │  {content: "@scout best            │                       │
     │   restaurants in Barcelona"}        │                       │
     │───────────────────────────────────>│                       │
     │                                    │                       │
     │                                    │  ConsentGate          │
     │                                    │  .check_consent()     │
     │                                    │                       │
     │                                    │  SELECT ai_consent    │
     │                                    │  WHERE group_id = X   │
     │                                    │──────────────────────>│
     │                                    │                       │
     │                  ┌─────────── NO CONSENT FOUND ──────────┐ │
     │                  │                                        │ │
     │                  │  Return system message:                 │ │
     │                  │  "AI features require group consent"   │ │
     │                  │  + ScoutConsentCard in chat             │ │
     │                  │                                        │ │
     │  200 OK          │                                        │ │
     │  {message +      │                                        │ │
     │   consent_card}  │                                        │ │
     │<─────────────────│                                        │ │
     │                                                            │ │
     │  User clicks "Grant Consent"                               │ │
     │                                                            │ │
     │  POST /ai-consent/{group_id}                               │ │
     │  {consented: true}                                         │ │
     │───────────────────────────────────>│                       │
     │                                    │  INSERT ai_consent    │
     │                                    │──────────────────────>│
     │  200 OK                            │                       │
     │<───────────────────────────────────│                       │
     │                                                            │ │
     │  Next @scout message → proceeds to Scout Agent             │ │
     └────────────────────────────────────────────────────────────┘ │
```

---

## Scout Agent Flow

```
Chat Message with @scout           Flask Backend              Celery Worker
     │                                  │                          │
     │  POST /gp/groups/{id}/chat       │                          │
     │  {content: "@scout suggest       │                          │
     │   tapas bars near La Rambla"}    │                          │
     │─────────────────────────────────>│                          │
     │                                  │                          │
     │                                  │  ChatService.send()      │
     │                                  │  Detect @scout mention   │
     │                                  │                          │
     │                                  │  process_scout_mention   │
     │                                  │  .delay(group_id,        │
     │                                  │   content, user_id)      │
     │                                  │─────────────────────────>│
     │                                  │                          │
     │  201 Created {user_message}      │                          │
     │<─────────────────────────────────│                          │
     │                                  │                          │
     │                                  │    Celery Worker:        │
     │                                  │    ┌──────────────────┐  │
     │                                  │    │ 1. Load group    │  │
     │                                  │    │    context        │  │
     │                                  │    │    (places,       │  │
     │                                  │    │     members,      │  │
     │                                  │    │     itinerary)    │  │
     │                                  │    │                   │  │
     │                                  │    │ 2. Build prompt   │  │
     │                                  │    │    (Jinja2        │  │
     │                                  │    │     template)     │  │
     │                                  │    │                   │  │
     │                                  │    │ 3. Check circuit  │  │
     │                                  │    │    breaker        │  │
     │                                  │    │    (pybreaker)    │  │
     │                                  │    │                   │  │
     │                                  │    │ 4. Call Ollama    │  │
     │                                  │    │    POST /api/     │  │
     │                                  │    │    generate       │  │
     │                                  │    │                   │  │
     │                                  │    │ 5. Validate JSON  │  │
     │                                  │    │    output         │  │
     │                                  │    │    (schema check) │  │
     │                                  │    │                   │  │
     │                                  │    │ 6. Insert AI      │  │
     │                                  │    │    response as    │  │
     │                                  │    │    chat message   │  │
     │                                  │    │    (type:         │  │
     │                                  │    │     ai_response)  │  │
     │                                  │    │                   │  │
     │                                  │    │ 7. Log to         │  │
     │                                  │    │    ai_agent_log   │  │
     │                                  │    │    (latency,      │  │
     │                                  │    │     tokens,       │  │
     │                                  │    │     success)      │  │
     │                                  │    └──────────────────┘  │
     │                                  │                          │
     │  WSS: chat:message               │                          │
     │  {type: "ai_response",           │                          │
     │   content: "Here are 3 tapas     │                          │
     │   bars near La Rambla:           │                          │
     │   1. Bar Pinotxo - ..."          │                          │
     │   metadata: {places: [...]}}     │                          │
     │<═════════════════════════════════│                          │
```

---

## Crew Agent Flow

```
Chat Message with @crew            Flask Backend              Crew AI API
     │                                  │                          │
     │  POST /gp/groups/{id}/chat       │                          │
     │  {content: "@crew plan day 3     │                          │
     │   around Park Guell"}            │                          │
     │─────────────────────────────────>│                          │
     │                                  │                          │
     │                                  │  process_crew_mention    │
     │                                  │  .delay()                │
     │                                  │                          │
     │                                  │  CrewAgentService        │
     │                                  │  .process_mention()      │
     │                                  │                          │
     │                                  │  CrewConversation        │
     │                                  │  .get_or_create()        │
     │                                  │  (stateful session)      │
     │                                  │                          │
     │                                  │  POST crew_api_url       │
     │                                  │  {conversation_id,       │
     │                                  │   message,               │
     │                                  │   group_context}         │
     │                                  │─────────────────────────>│
     │                                  │                          │
     │                                  │  Response type:          │
     │                                  │  "question" →            │
     │                                  │  render QuestionCard     │
     │                                  │                          │
     │  WSS: chat:message               │                          │
     │  {type: "ai_card",               │                          │
     │   metadata: {                    │                          │
     │     cardType: "question",        │                          │
     │     text: "What time should      │                          │
     │       day 3 start?",             │                          │
     │     options: ["8am","9am","10am"] │                         │
     │   }}                             │                          │
     │<═════════════════════════════════│                          │
     │                                  │                          │
     │  User selects "9am"              │                          │
     │  (continues multi-turn convo)    │                          │
     │                                  │                          │
     │  ... more turns ...              │                          │
     │                                  │                          │
     │  Final response:                 │                          │
     │  {cardType: "confirm",           │                          │
     │   action: "update_itinerary",    │                          │
     │   details: {day: 3, stops: [...]}}│                         │
     │<═════════════════════════════════│                          │
     │                                  │                          │
     │  User clicks "Confirm"           │                          │
     │                                  │                          │
     │  POST /ai-confirm/{group_id}     │                          │
     │  {action: "update_itinerary",    │                          │
     │   payload: {...}}                │                          │
     │─────────────────────────────────>│                          │
     │                                  │                          │
     │                                  │  Execute action:         │
     │                                  │  Update itinerary doc    │
     │                                  │  Emit itinerary:updated  │
     │                                  │                          │
     │  200 OK {success: true}          │                          │
     │<─────────────────────────────────│                          │
```

---

## Components

### Backend

| File | Purpose |
|------|---------|
| `app/api/v1/gp_chat.py` | Chat endpoints with @scout/@crew detection |
| `app/api/v1/ai_consent.py` | AI consent GET/POST/DELETE (3 endpoints) |
| `app/api/v1/ai_confirm.py` | Execute confirmed AI actions (1 endpoint) |
| `app/services/scout_agent_service.py` | ScoutAgentService: process_mention, generate_suggestions, call_ollama |
| `app/services/crew_agent_service.py` | CrewAgentService: process_mention, call_crew_api, parse_response |
| `app/services/crew_conversation.py` | CrewConversation: multi-turn conversation state management |
| `app/services/crew_parsers.py` | Response parsing: markdown to JSON, structured extraction |
| `app/services/consent_gate.py` | ConsentGate: check_consent, require_consent enforcement |
| `app/domain/ai/models.py` | AIConsent, AIPreferenceProfile, AIAgentLog |
| `app/infrastructure/llm/ollama_client.py` | OllamaClient with circuit breaker (pybreaker) |
| `app/infrastructure/llm/prompt_templates.py` | Jinja2 prompt templates for Scout |
| `app/infrastructure/llm/output_validator.py` | JSON schema validation for LLM outputs |
| `app/workers/tasks/ai_tasks.py` | process_scout_mention, generate_chat_summary, cleanup_agent_logs |
| `app/workers/tasks/crew_tasks.py` | process_crew_mention |
| `app/core/resilience.py` | Circuit breaker and retry configuration |

### Frontend

| File | Purpose |
|------|---------|
| `src/components/groupPlanner/jsx/chat/ChatPanel.jsx` | Chat UI with @mention detection and rendering |
| `src/components/groupPlanner/jsx/chat/CrewCards.jsx` | AI card renderer: Question, Confirm, Place, Success cards |
| `src/components/groupPlanner/jsx/chat/ScoutConsentCard.jsx` | Consent request UI |
| `src/services/aiConsentApi.js` | AI consent REST calls |
| `src/hooks/useAiConsentQuery.js` | TanStack Query: useGetConsent, useSubmitConsent, useRevokeConsent |
| `src/hooks/useChatState.js` | Local chat state with @mention detection logic |

---

## AI Card Types

| Card Type | Trigger | Content | Action |
|-----------|---------|---------|--------|
| **Question** | Crew needs clarification | Question text + options | User selects option → continues conversation |
| **Confirm** | Crew proposes action | Action description + details | User confirms → POST /ai-confirm executes |
| **Place** | Scout/Crew suggests place | Place card with name, rating, description | User can add to Library |
| **Success** | Action confirmed and executed | Success message | Display only |

## Crew Confirmable Actions

| Action | What It Does |
|--------|-------------|
| `update_itinerary` | Modify day plan in itinerary document |
| `add_place` | Add a suggested place to group Library |
| `delete_place` | Remove a place from group Library |
| `create_poll` | Create a new poll for group decision |
| `add_event` | Add an external event to the itinerary |

---

## Circuit Breaker (Scout Agent)

```
CLOSED (normal) ──── 5 consecutive failures ────> OPEN (no calls)
                                                      │
                                                 60 seconds
                                                      │
                                               HALF-OPEN ────────> CLOSED
                                              (1 test call)     (if success)
                                                      │
                                                      └──────> OPEN
                                                            (if failure)
```

When the circuit is open, the Scout agent returns a graceful fallback message:
> "AI suggestions are temporarily unavailable. Please try again later."

---

## Database Models (AI Module)

```
ai_consent
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── user_id (FK → users.id)
├── consented (Boolean)
└── created_at, updated_at

ai_preference_profile
├── id (UUIDv7, PK)
├── user_id (FK → users.id)
├── preferences (JSON: cuisine, budget, pace, interests)
└── created_at, updated_at

ai_agent_log
├── id (UUIDv7, PK)
├── group_id (FK → travel_groups.id)
├── user_id (FK → users.id)
├── agent_type (String: scout, crew)
├── input_text (Text)
├── output_text (Text)
├── latency_ms (Integer)
├── token_count (Integer)
├── success (Boolean)
├── error_message (Text, nullable)
└── created_at
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/ai-consent/{group_id}/status` | Required | Check consent status |
| POST | `/ai-consent/{group_id}` | Required | Grant/revoke consent |
| DELETE | `/ai-consent/{group_id}` | Required | Revoke consent |
| POST | `/ai-confirm/{group_id}` | Required | Execute confirmed AI action |
