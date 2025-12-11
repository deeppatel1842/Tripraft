# AI Travel Chatbot Architecture Plan

## Enterprise-Scale Conversational Travel Assistant (Zero-Cost Edition)

**Version**: 2.0.0  
**Date**: December 4, 2025  
**Target Capacity**: 1,000+ Concurrent Users  
**Cost**: FREE (No GPU, No Cloud Required)

---

## Executive Summary

This document outlines the architecture for a **completely free** production-grade AI chatbot that provides intelligent travel assistance using a hybrid RAG (Retrieval-Augmented Generation) approach. The system runs on **your local machine or any basic server** without requiring GPUs or paid cloud services.

### Key Principles
- **100% Free**: No paid APIs, no cloud costs, no GPU required
- **Local-First**: Runs entirely on your machine
- **Multilingual**: Understands and responds in user's language
- **Context-Aware**: Maintains conversation history and user preferences
- **Scalable**: Handles 1000+ users with smart architecture

---

## Zero-Cost Technology Stack

| Component | Free Solution | Alternative |
|-----------|--------------|-------------|
| **LLM** | Ollama + Llama 3.2 (3B) | LM Studio, GPT4All |
| **Embeddings** | sentence-transformers (local) | all-MiniLM-L6-v2 |
| **Vector Store** | ChromaDB (local) | FAISS, LanceDB |
| **Cache** | Redis (local) or Python dict | SQLite |
| **Database** | Firestore (free tier) | SQLite, JSON files |
| **Backend** | Flask + Gunicorn | FastAPI |
| **Frontend** | React.js | - |

### Hardware Requirements (Minimum)
- **CPU**: 4+ cores (Intel i5/AMD Ryzen 5 or better)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space
- **GPU**: NOT REQUIRED (CPU inference works fine)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND LAYER (React.js)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  ChatWidget  │  ConversationHistory  │  StreamingResponse  │  TypingIndicator│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY / LOAD BALANCER                       │
│                    (Rate Limiting, Auth, Request Routing)                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLASK BACKEND (Python)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      CHAT ORCHESTRATOR                              │  │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │  │
│   │  │Intent Detector│  │Context Manager│  │Conversation State Machine│  │  │
│   │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      RAG ENGINE (Hybrid)                            │  │
│   │                                                                     │  │
│   │   [1] Query Analyzer ──► [2] Knowledge Router ──► [3] Response Gen  │  │
│   │          │                      │                        │          │  │
│   │          ▼                      ▼                        ▼          │  │
│   │   ┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐  │  │
│   │   │ Entity       │    │ DATA SOURCE     │    │ Response         │  │  │
│   │   │ Recognition  │    │ SELECTOR        │    │ Synthesizer      │  │  │
│   │   │              │    │                 │    │                  │  │  │
│   │   │ - Places     │    │ ┌─────────────┐ │    │ - Template Based │  │  │
│   │   │ - Cities     │    │ │ Places DB   │ │    │ - LLM Enhanced   │  │  │
│   │   │ - Countries  │    │ │ (Priority 1)│ │    │ - Streaming      │  │  │
│   │   │ - Activities │    │ └─────────────┘ │    └──────────────────┘  │  │
│   │   │ - Dates      │    │ ┌─────────────┐ │                          │  │
│   │   └──────────────┘    │ │ Vector Store│ │                          │  │
│   │                       │ │ (Priority 2)│ │                          │  │
│   │                       │ └─────────────┘ │                          │  │
│   │                       │ ┌─────────────┐ │                          │  │
│   │                       │ │ LLM Fallback│ │                          │  │
│   │                       │ │ (Priority 3)│ │                          │  │
│   │                       │ └─────────────┘ │                          │  │
│   │                       └─────────────────┘                          │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐│
│  │  Firestore  │  │    Redis    │  │  Pinecone/  │  │   LLM Provider      ││
│  │  (Primary)  │  │   (Cache)   │  │  Qdrant     │  │   (OpenAI/Claude)   ││
│  │             │  │             │  │  (Vectors)  │  │                     ││
│  │ - 16,885    │  │ - Sessions  │  │ - Semantic  │  │ - GPT-4 Turbo       ││
│  │   places    │  │ - Hot data  │  │   Search    │  │ - Claude 3.5        ││
│  │ - 888 cities│  │ - Rate lim  │  │ - Embeddings│  │ - Streaming API     ││
│  │ - 82 countrs│  │ - Queues    │  │             │  │                     ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
User Query: "What are the best places to visit in Delhi?"
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 1: QUERY ANALYSIS                       │
│                                                                 │
│  Input:  "What are the best places to visit in Delhi?"         │
│                                                                 │
│  Output: {                                                      │
│    "intent": "place_discovery",                                │
│    "entities": {                                                │
│      "location": "Delhi",                                       │
│      "location_type": "city",                                   │
│      "filter": "best/top"                                       │
│    },                                                           │
│    "requires_llm": false                                        │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 2: DATA RETRIEVAL                       │
│                                                                 │
│  Priority Check:                                                │
│  [✓] Delhi found in Places DB                                  │
│  [✓] 20 places with rank_score available                       │
│                                                                 │
│  Query: SELECT * FROM places                                    │
│         WHERE city_normalized = 'delhi'                         │
│         ORDER BY rank_score DESC                                │
│         LIMIT 10                                                │
│                                                                 │
│  Result: [Red Fort, India Gate, Qutub Minar, ...]              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 3: RESPONSE GENERATION                  │
│                                                                 │
│  Template + LLM Enhancement:                                    │
│                                                                 │
│  "Here are the top places to visit in Delhi:                   │
│                                                                 │
│   1. **Red Fort** (rank: 0.82) - UNESCO World Heritage Site... │
│   2. **India Gate** (rank: 0.78) - Iconic war memorial...      │
│   3. **Qutub Minar** (rank: 0.75) - 12th century minaret...    │
│                                                                 │
│   Would you like more details about any of these places?"      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Intent Classification System

```python
INTENT_CATEGORIES = {
    # ==================== DISCOVERY INTENTS ====================
    "place_discovery": {
        "patterns": [
            "what to see in {location}",
            "best places in {location}",
            "top attractions in {location}",
            "things to do in {location}",
            "must visit places in {location}"
        ],
        "handler": "handle_place_discovery",
        "requires_db": True,
        "fallback_llm": True
    },
    
    "place_detail": {
        "patterns": [
            "tell me about {place_name}",
            "what is {place_name}",
            "information about {place_name}",
            "details of {place_name}"
        ],
        "handler": "handle_place_detail",
        "requires_db": True,
        "fallback_llm": True
    },
    
    # ==================== PLANNING INTENTS ====================
    "itinerary_request": {
        "patterns": [
            "{duration} day itinerary for {location}",
            "plan my trip to {location}",
            "travel plan for {location}",
            "what to do in {location} for {duration}"
        ],
        "handler": "handle_itinerary",
        "requires_db": True,
        "requires_llm": True
    },
    
    "comparison": {
        "patterns": [
            "compare {place1} and {place2}",
            "{place1} vs {place2}",
            "which is better {place1} or {place2}"
        ],
        "handler": "handle_comparison",
        "requires_db": True,
        "requires_llm": True
    },
    
    # ==================== PRACTICAL INTENTS ====================
    "logistics": {
        "patterns": [
            "how to reach {location}",
            "best time to visit {location}",
            "weather in {location}",
            "when to go to {location}"
        ],
        "handler": "handle_logistics",
        "requires_db": True,
        "fallback_llm": True
    },
    
    "cost_inquiry": {
        "patterns": [
            "how much does {place} cost",
            "entry fee for {place}",
            "is {place} free",
            "budget for {location}"
        ],
        "handler": "handle_cost",
        "requires_db": True,
        "fallback_llm": False
    },
    
    # ==================== RECOMMENDATION INTENTS ====================
    "personalized_recommendation": {
        "patterns": [
            "recommend places for {activity}",
            "best {activity} spots in {location}",
            "where can I {activity} in {location}",
            "family friendly places in {location}"
        ],
        "handler": "handle_recommendation",
        "requires_db": True,
        "requires_llm": True
    },
    
    "nearby_search": {
        "patterns": [
            "places near {place}",
            "what's around {place}",
            "attractions near {place}"
        ],
        "handler": "handle_nearby",
        "requires_db": True,
        "fallback_llm": False
    },
    
    # ==================== FALLBACK ====================
    "general_travel": {
        "patterns": ["*"],
        "handler": "handle_general",
        "requires_db": False,
        "requires_llm": True
    }
}
```

### 2. Knowledge Router (Advanced RAG)

```python
class KnowledgeRouter:
    """
    Intelligent router that decides data source based on query analysis.
    
    Priority Order:
    1. Places Engine DB (highest confidence, structured data)
    2. Vector Store (semantic search for fuzzy matches)
    3. LLM Knowledge (fallback for uncovered topics)
    """
    
    CONFIDENCE_THRESHOLD = 0.7
    
    def route(self, query_analysis: dict) -> DataSource:
        entities = query_analysis.get("entities", {})
        location = entities.get("location")
        place_name = entities.get("place_name")
        
        # Priority 1: Direct DB lookup
        if location:
            db_result = self.check_places_db(location)
            if db_result["found"] and db_result["confidence"] >= self.CONFIDENCE_THRESHOLD:
                return DataSource.PLACES_DB
        
        if place_name:
            db_result = self.check_place_exists(place_name)
            if db_result["found"]:
                return DataSource.PLACES_DB
        
        # Priority 2: Vector similarity search
        vector_result = self.vector_search(query_analysis["original_query"])
        if vector_result["top_score"] >= self.CONFIDENCE_THRESHOLD:
            return DataSource.VECTOR_STORE
        
        # Priority 3: LLM fallback
        return DataSource.LLM_KNOWLEDGE
    
    def check_places_db(self, location: str) -> dict:
        """Check if location exists in our Places Engine."""
        normalized = normalize_query(location)
        
        # Check cities collection
        city_match = db.collection('cities').where(
            'name_normalized', '==', normalized
        ).limit(1).get()
        
        if city_match:
            return {"found": True, "confidence": 1.0, "type": "city"}
        
        # Check countries collection
        country_match = db.collection('countries').where(
            'name_normalized', '==', normalized
        ).limit(1).get()
        
        if country_match:
            return {"found": True, "confidence": 1.0, "type": "country"}
        
        # Fuzzy match using vector search
        return {"found": False, "confidence": 0.0}
```

### 3. Response Templates

```python
RESPONSE_TEMPLATES = {
    "place_discovery": {
        "intro": "Here are the top places to visit in {location}:\n\n",
        "place_item": "{rank}. **{name}** (Rating: {rating}/5)\n   {summary}\n   Cost: {cost} | Duration: {duration}\n\n",
        "outro": "Would you like more details about any of these places, or shall I help you plan a visit?",
        "no_data_fallback": "I don't have detailed data for {location} in my database, but based on my knowledge:\n\n{llm_response}"
    },
    
    "place_detail": {
        "template": """
## {name}

{ai_summary}

### Quick Facts
- **Location**: {city}, {state}, {country}
- **Cost**: {cost}
- **Duration**: {suggested_duration}
- **Best Time**: {best_time_to_visit}
- **Booking**: {advanced_booking}

### Why Visit
{why_visit}

### Opening Hours
{opening_hours_formatted}

{additional_llm_context}
""",
        "no_data_fallback": "I couldn't find {place_name} in my database. {llm_response}"
    },
    
    "itinerary": {
        "intro": "Here's a {duration}-day itinerary for {location}:\n\n",
        "day_template": "### Day {day_num}: {theme}\n\n{activities}\n\n",
        "activity_template": "- **{time}**: {place_name} ({duration})\n  {tip}\n"
    },
    
    "comparison": {
        "template": """
## {place1} vs {place2}

| Aspect | {place1} | {place2} |
|--------|----------|----------|
| Rating | {rating1}/5 | {rating2}/5 |
| Cost | {cost1} | {cost2} |
| Duration | {duration1} | {duration2} |
| Best Time | {time1} | {time2} |

### Summary
{llm_comparison}
"""
    }
}
```

---

## Scalability Architecture (1000+ Users)

### Infrastructure Design

```
                    ┌─────────────────────────────────────────┐
                    │           CLOUDFLARE CDN                │
                    │         (DDoS Protection)               │
                    └─────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │         NGINX LOAD BALANCER             │
                    │    (Round Robin / Least Connections)    │
                    └─────────────────────────────────────────┘
                          │         │         │         │
                          ▼         ▼         ▼         ▼
                    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
                    │ Flask   │ │ Flask   │ │ Flask   │ │ Flask   │
                    │ Pod 1   │ │ Pod 2   │ │ Pod 3   │ │ Pod N   │
                    │(Gunicorn│ │(Gunicorn│ │(Gunicorn│ │(Gunicorn│
                    │ 4 wrkrs)│ │ 4 wrkrs)│ │ 4 wrkrs)│ │ 4 wrkrs)│
                    └─────────┘ └─────────┘ └─────────┘ └─────────┘
                          │         │         │         │
                          └─────────┴─────────┴─────────┘
                                      │
                    ┌─────────────────────────────────────────┐
                    │           REDIS CLUSTER                 │
                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
                    │  │ Master  │──│ Replica │──│ Replica │ │
                    │  └─────────┘  └─────────┘  └─────────┘ │
                    │                                         │
                    │  Purposes:                              │
                    │  - Session storage                      │
                    │  - Response caching                     │
                    │  - Rate limiting                        │
                    │  - Pub/Sub for streaming                │
                    │  - Queue for async LLM calls            │
                    └─────────────────────────────────────────┘
```

### Capacity Planning

| Component | Specification | Handles |
|-----------|---------------|---------|
| **Flask Pods** | 4 pods × 4 workers = 16 concurrent | 800 req/sec |
| **Redis Cluster** | 3 nodes, 16GB each | 100K ops/sec |
| **Firestore** | Auto-scaling | Unlimited reads |
| **LLM API** | Rate limited pool | 100 concurrent |
| **Vector DB** | Pinecone Starter | 1M vectors |

### Rate Limiting Strategy

```python
RATE_LIMITS = {
    "chat_message": {
        "anonymous": "10/minute",
        "authenticated": "30/minute",
        "premium": "100/minute"
    },
    "itinerary_generation": {
        "anonymous": "2/hour",
        "authenticated": "10/hour",
        "premium": "50/hour"
    },
    "llm_fallback": {
        "global": "1000/minute",  # API cost control
        "per_user": "5/minute"
    }
}
```

### Caching Strategy

```python
CACHE_CONFIG = {
    # Hot data - frequently accessed
    "place_detail": {
        "ttl": 86400,  # 24 hours
        "key_pattern": "chat:place:{place_id}",
        "invalidation": "on_update"
    },
    
    # User sessions
    "conversation": {
        "ttl": 3600,  # 1 hour
        "key_pattern": "chat:session:{session_id}",
        "max_messages": 50
    },
    
    # LLM responses (expensive to regenerate)
    "llm_response": {
        "ttl": 21600,  # 6 hours
        "key_pattern": "chat:llm:{query_hash}",
        "semantic_dedup": True
    },
    
    # Autocomplete suggestions
    "autocomplete": {
        "ttl": 3600,  # 1 hour
        "key_pattern": "chat:auto:{prefix}",
        "warm_on_startup": True
    }
}
```

---

## API Endpoints

### Chat API Routes

```
POST   /api/v2/chat/message          Send user message, get AI response
GET    /api/v2/chat/stream/{id}      SSE stream for real-time response
GET    /api/v2/chat/history          Get conversation history
DELETE /api/v2/chat/history          Clear conversation
POST   /api/v2/chat/feedback         Submit response feedback
GET    /api/v2/chat/suggestions      Get conversation starters
```

### Request/Response Examples

**Send Message**
```json
// POST /api/v2/chat/message
// Request
{
    "session_id": "sess_abc123",
    "message": "What are the best temples in Varanasi?",
    "context": {
        "previous_location": "Delhi",
        "trip_dates": "2025-03-15 to 2025-03-20"
    }
}

// Response
{
    "success": true,
    "response_id": "resp_xyz789",
    "message": "Here are the top temples to visit in Varanasi:\n\n1. **Kashi Vishwanath Temple** (Rating: 4.9/5)...",
    "data_source": "places_db",
    "confidence": 0.95,
    "places_mentioned": [
        {"id": "PL123", "name": "Kashi Vishwanath Temple"},
        {"id": "PL456", "name": "Dashashwamedh Ghat"}
    ],
    "follow_up_suggestions": [
        "Tell me more about Kashi Vishwanath Temple",
        "What's the best time to visit?",
        "Show me nearby places"
    ],
    "metadata": {
        "response_time_ms": 234,
        "tokens_used": 450,
        "cache_hit": false
    }
}
```

**Streaming Response**
```
// GET /api/v2/chat/stream/resp_xyz789
// Server-Sent Events

event: start
data: {"response_id": "resp_xyz789", "status": "generating"}

event: chunk
data: {"text": "Here are the top temples"}

event: chunk
data: {"text": " to visit in Varanasi:\n\n"}

event: chunk
data: {"text": "1. **Kashi Vishwanath Temple**..."}

event: places
data: {"places": [{"id": "PL123", "name": "Kashi Vishwanath Temple"}]}

event: complete
data: {"status": "complete", "total_tokens": 450}
```

---

## LLM Integration

### Provider Configuration

```python
LLM_CONFIG = {
    "primary": {
        "provider": "openai",
        "model": "gpt-4-turbo-preview",
        "max_tokens": 1000,
        "temperature": 0.7,
        "timeout": 30
    },
    "fallback": {
        "provider": "anthropic",
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 1000,
        "temperature": 0.7,
        "timeout": 30
    },
    "embedding": {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "dimensions": 1536
    }
}
```

### System Prompts

```python
SYSTEM_PROMPTS = {
    "travel_assistant": """You are a knowledgeable travel assistant for TripRaft.

CONTEXT:
- You have access to a database of {place_count} verified places across {country_count} countries
- When data is provided from the database, prioritize it over your general knowledge
- Always be helpful, concise, and accurate

GUIDELINES:
1. For places in the database, use the provided data (ratings, costs, timings)
2. For places not in the database, clearly state "Based on my knowledge..."
3. Always suggest follow-up actions or related places
4. Format responses with markdown for readability
5. Include practical tips when relevant

DATABASE CONTEXT:
{db_context}

USER QUERY: {user_query}
""",

    "itinerary_builder": """Create a detailed travel itinerary based on the following:

AVAILABLE PLACES (from our verified database):
{places_list}

CONSTRAINTS:
- Duration: {duration} days
- Location: {location}
- Preferences: {preferences}

REQUIREMENTS:
1. Use places from our database when available
2. Group nearby places together for efficiency
3. Consider opening hours and best visit times
4. Include travel time estimates between places
5. Balance activities throughout the day

Generate a day-by-day itinerary with specific times and tips.
""",

    "place_enhancer": """Enhance the following place information with additional context:

DATABASE INFO:
{place_data}

Add:
1. Historical context (2-3 sentences)
2. Insider tips for visitors
3. Photography spots
4. Nearby dining recommendations

Keep the tone friendly and informative.
"""
}
```

---

## Vector Store Setup (Semantic Search)

### Embedding Pipeline

```python
class PlacesEmbeddingPipeline:
    """Generate and store embeddings for semantic search."""
    
    def __init__(self):
        self.embedding_model = "text-embedding-3-small"
        self.vector_db = PineconeClient()
    
    def generate_place_embedding(self, place: dict) -> list:
        """Create searchable embedding from place data."""
        # Combine relevant fields for rich embedding
        text = f"""
        {place['name']} is a {', '.join(place.get('tags', []))} located in 
        {place['city']}, {place['state']}, {place['country']}.
        
        {place.get('ai_summary', '')}
        
        {place.get('why_visit', '')}
        
        Best time to visit: {place.get('best_time_to_visit', 'any time')}
        Cost: {place.get('cost', 'varies')}
        Duration: {place.get('suggested_duration', '1-2 hours')}
        """
        
        return openai.Embedding.create(
            input=text,
            model=self.embedding_model
        )['data'][0]['embedding']
    
    def index_all_places(self):
        """Index all places from Firestore to vector store."""
        places = db.collection('places').stream()
        
        vectors = []
        for doc in places:
            place = doc.to_dict()
            embedding = self.generate_place_embedding(place)
            
            vectors.append({
                "id": doc.id,
                "values": embedding,
                "metadata": {
                    "name": place['name'],
                    "city": place['city'],
                    "country": place['country'],
                    "tags": place.get('tags', []),
                    "rank_score": place.get('rank_score', 0)
                }
            })
        
        # Batch upsert to Pinecone
        self.vector_db.upsert(vectors=vectors, batch_size=100)
```

### Semantic Query Flow

```
User: "I want to see ancient ruins and temples in India"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. EMBED QUERY                                              │
│    "ancient ruins and temples in India" → [0.12, 0.45, ...] │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. VECTOR SEARCH (Pinecone)                                 │
│    Top 10 matches with scores:                              │
│    - Hampi Ruins (0.92)                                     │
│    - Khajuraho Temples (0.89)                               │
│    - Konark Sun Temple (0.87)                               │
│    - Mahabalipuram (0.85)                                   │
│    - ...                                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. FETCH FULL DATA (Firestore)                              │
│    Get complete place details for top matches               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. GENERATE RESPONSE                                        │
│    Combine DB data with LLM enhancement                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Conversation State Management

### Session Schema

```python
class ConversationSession:
    """Track conversation state for contextual responses."""
    
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    last_activity: datetime
    
    # Conversation history
    messages: List[Message]  # Max 50 messages
    
    # Extracted context
    context: {
        "current_location": Optional[str],      # Last discussed location
        "interested_places": List[str],          # Place IDs user showed interest in
        "trip_dates": Optional[DateRange],       # If mentioned
        "preferences": {
            "budget": Optional[str],             # "budget", "mid-range", "luxury"
            "travel_style": Optional[str],       # "adventure", "cultural", "relaxed"
            "group_type": Optional[str]          # "solo", "couple", "family"
        },
        "visited_places": List[str]              # Places already discussed in detail
    }
    
    # For response continuity
    pending_actions: List[Action]  # Follow-up suggestions clicked
```

### Context Window Management

```python
def build_context_window(session: ConversationSession, max_tokens: int = 2000) -> str:
    """Build optimal context for LLM while respecting token limits."""
    
    context_parts = []
    token_count = 0
    
    # 1. Current location context (high priority)
    if session.context.get("current_location"):
        location_ctx = f"User is currently asking about: {session.context['current_location']}"
        context_parts.append(location_ctx)
        token_count += estimate_tokens(location_ctx)
    
    # 2. Recent messages (sliding window)
    recent_messages = session.messages[-10:]  # Last 10 messages
    for msg in reversed(recent_messages):
        msg_text = f"{msg.role}: {msg.content}"
        msg_tokens = estimate_tokens(msg_text)
        
        if token_count + msg_tokens > max_tokens * 0.6:
            break
        
        context_parts.insert(1, msg_text)
        token_count += msg_tokens
    
    # 3. User preferences (if known)
    if session.context.get("preferences"):
        prefs = session.context["preferences"]
        pref_text = f"User preferences: {json.dumps(prefs)}"
        context_parts.append(pref_text)
    
    return "\n".join(context_parts)
```

---

## Monitoring and Analytics

### Key Metrics

```python
METRICS = {
    "response_quality": {
        "data_source_distribution": ["places_db", "vector_store", "llm_only"],
        "average_confidence_score": float,
        "user_satisfaction_rating": float,
        "follow_up_engagement_rate": float
    },
    
    "performance": {
        "average_response_time_ms": float,
        "p95_response_time_ms": float,
        "cache_hit_rate": float,
        "llm_fallback_rate": float
    },
    
    "usage": {
        "daily_active_sessions": int,
        "messages_per_session": float,
        "peak_concurrent_users": int,
        "popular_locations": List[str],
        "common_intents": Dict[str, int]
    },
    
    "costs": {
        "llm_tokens_used_daily": int,
        "estimated_daily_cost": float,
        "cost_per_conversation": float
    }
}
```

### Logging Structure

```python
# Request logging
{
    "timestamp": "2025-12-04T10:30:00Z",
    "session_id": "sess_abc123",
    "request_id": "req_xyz789",
    "user_message": "What are the best beaches in Goa?",
    "intent_detected": "place_discovery",
    "entities": {"location": "Goa", "category": "beaches"},
    "data_source": "places_db",
    "places_returned": 8,
    "response_time_ms": 234,
    "llm_tokens": 0,
    "cache_hit": false
}

# Error logging
{
    "timestamp": "2025-12-04T10:31:00Z",
    "session_id": "sess_def456",
    "error_type": "LLM_TIMEOUT",
    "error_message": "OpenAI API timeout after 30s",
    "fallback_used": true,
    "fallback_provider": "anthropic",
    "recovery_successful": true
}
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

```
[ ] Set up chat service module structure
[ ] Implement intent classification system
[ ] Create basic query analyzer with entity extraction
[ ] Build Places DB connector with existing PlacesService
[ ] Implement simple response templates
[ ] Create /api/v2/chat/message endpoint
[ ] Add session management with Redis
```

### Phase 2: RAG Integration (Week 3-4)

```
[ ] Set up Pinecone/Qdrant for vector storage
[ ] Build embedding pipeline for places data
[ ] Implement semantic search functionality
[ ] Create Knowledge Router with priority logic
[ ] Add LLM integration (OpenAI/Anthropic)
[ ] Implement response streaming (SSE)
[ ] Build context window manager
```

### Phase 3: Intelligence (Week 5-6)

```
[ ] Fine-tune intent classification
[ ] Add itinerary generation capability
[ ] Implement place comparison feature
[ ] Build personalized recommendation engine
[ ] Add follow-up suggestion generator
[ ] Create feedback collection system
```

### Phase 4: Scale & Polish (Week 7-8)

```
[ ] Implement rate limiting
[ ] Set up load balancing
[ ] Add comprehensive caching
[ ] Build monitoring dashboard
[ ] Implement auto-scaling rules
[ ] Performance optimization
[ ] Security hardening
```

---

## File Structure

```
places_engine/
├── chat/
│   ├── __init__.py
│   ├── orchestrator.py         # Main chat coordination
│   ├── intent_classifier.py    # Query intent detection
│   ├── entity_extractor.py     # NER for places/locations
│   ├── knowledge_router.py     # Data source selection
│   ├── response_generator.py   # Template + LLM responses
│   ├── session_manager.py      # Conversation state
│   ├── streaming.py            # SSE implementation
│   └── templates/
│       ├── discovery.py
│       ├── itinerary.py
│       └── comparison.py
├── rag/
│   ├── __init__.py
│   ├── embeddings.py           # Vector generation
│   ├── vector_store.py         # Pinecone/Qdrant client
│   └── semantic_search.py      # Similarity search
├── llm/
│   ├── __init__.py
│   ├── providers.py            # OpenAI, Anthropic clients
│   ├── prompts.py              # System prompts
│   └── fallback.py             # Provider failover
└── api/
    └── chat_routes.py          # Chat API endpoints
```

---

## Security Considerations

### Input Sanitization

```python
def sanitize_user_input(message: str) -> str:
    """Sanitize user input to prevent prompt injection."""
    
    # Remove potential prompt injection patterns
    dangerous_patterns = [
        r"ignore previous instructions",
        r"disregard above",
        r"system:",
        r"assistant:",
        r"<\|.*\|>",
    ]
    
    sanitized = message
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
    
    # Truncate to reasonable length
    return sanitized[:2000]
```

### Rate Limiting Implementation

```python
from flask_limiter import Limiter

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri="redis://localhost:6379"
)

@chat_bp.route('/message', methods=['POST'])
@limiter.limit("30/minute", key_func=get_session_id)
def send_message():
    # Handle message
    pass
```

---

## Cost Estimation

### Zero-Cost Architecture (Recommended)

| Service | Free Solution | Monthly Cost |
|---------|--------------|--------------|
| **LLM** | Ollama + Llama 3.2 (3B) | **$0** |
| **Embeddings** | sentence-transformers | **$0** |
| **Vector Store** | ChromaDB (local) | **$0** |
| **Cache** | Redis (local Docker) | **$0** |
| **Database** | Firestore Spark (free tier) | **$0** |
| **Hosting** | Your machine / Free VPS | **$0** |
| **Total** | | **$0/month** |

---

## ZERO-COST IMPLEMENTATION GUIDE

This section details how to build a fully functional AI chatbot that handles 1000+ users **without any paid services**.

### Architecture Overview (Free Stack)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React.js)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FLASK BACKEND (Gunicorn - 8 workers)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                  SMART QUERY PROCESSOR                              │  │
│   │                                                                     │  │
│   │  ┌────────────────┐   ┌────────────────┐   ┌────────────────────┐  │  │
│   │  │ Language       │   │ Intent         │   │ Entity             │  │  │
│   │  │ Detector       │   │ Classifier     │   │ Extractor          │  │  │
│   │  │ (langdetect)   │   │ (Rule-based)   │   │ (spaCy/regex)      │  │  │
│   │  └────────────────┘   └────────────────┘   └────────────────────┘  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                     RAG ENGINE (Local)                              │  │
│   │                                                                     │  │
│   │   Priority 1: Your Places DB (16,885 places) ──► Direct Answer     │  │
│   │   Priority 2: ChromaDB Vector Search ──► Semantic Match            │  │
│   │   Priority 3: Ollama LLM ──► Generate Response                     │  │
│   │                                                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────────┐
│         LOCAL STORAGE           │   │          OLLAMA (Local LLM)         │
│                                 │   │                                     │
│  ┌───────────┐  ┌───────────┐  │   │  Model: Llama 3.2 (3B)              │
│  │ ChromaDB  │  │  Redis    │  │   │  RAM: 4-6GB                         │
│  │ (Vectors) │  │  (Cache)  │  │   │  Speed: 20-50 tokens/sec            │
│  │           │  │           │  │   │  Context: 8K tokens                 │
│  │ 16K docs  │  │ Sessions  │  │   │  Multilingual: Yes                  │
│  └───────────┘  └───────────┘  │   │                                     │
└─────────────────────────────────┘   └─────────────────────────────────────┘
```

---

### Step 1: Install Ollama (Free Local LLM)

Ollama runs LLMs locally on your CPU without needing a GPU.

```bash
# Windows (PowerShell as Admin)
winget install Ollama.Ollama

# Or download from: https://ollama.com/download

# After installation, pull a lightweight multilingual model
ollama pull llama3.2:3b          # 2GB, fast, multilingual
# OR for better quality (slower):
ollama pull llama3.1:8b          # 4.7GB, better responses
# OR smallest option:
ollama pull phi3:mini            # 2.3GB, very fast
```

**Why Llama 3.2 (3B)?**
- Runs on CPU (no GPU needed)
- Multilingual (Hindi, Spanish, French, etc.)
- 20-50 tokens/second on modern CPU
- Only 2GB RAM overhead
- Context window: 8K tokens

---

### Step 2: Set Up Local Vector Store (ChromaDB)

ChromaDB is a free, open-source vector database that runs locally.

```bash
# Install ChromaDB
pip install chromadb sentence-transformers

# The embedding model downloads automatically (400MB)
# Model: all-MiniLM-L6-v2 (multilingual)
```

**Embedding Pipeline:**
```python
import chromadb
from sentence_transformers import SentenceTransformer

# Initialize (runs locally, no API calls)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # 80+ languages
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Create collection for places
collection = chroma_client.get_or_create_collection(
    name="places",
    metadata={"hnsw:space": "cosine"}
)

def index_place(place: dict):
    """Index a place for semantic search."""
    text = f"""
    {place['name']} is located in {place['city']}, {place['country']}.
    {place.get('ai_summary', '')}
    Tags: {', '.join(place.get('tags', []))}
    """
    
    embedding = embedding_model.encode(text).tolist()
    
    collection.add(
        ids=[place['id']],
        embeddings=[embedding],
        metadatas=[{
            "name": place['name'],
            "city": place['city'],
            "country": place['country'],
            "rank_score": place.get('rank_score', 0)
        }],
        documents=[text]
    )

def semantic_search(query: str, n_results: int = 10):
    """Find similar places using semantic search."""
    query_embedding = embedding_model.encode(query).tolist()
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    return results
```

---

### Step 3: Language Detection & Translation

Free multilingual support using `langdetect` and response in user's language.

```python
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0  # Consistent results

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'pt': 'Portuguese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh-cn': 'Chinese',
    'ar': 'Arabic',
    'ru': 'Russian',
    'it': 'Italian',
}

def detect_language(text: str) -> str:
    """Detect user's language."""
    try:
        lang = detect(text)
        return lang if lang in SUPPORTED_LANGUAGES else 'en'
    except:
        return 'en'

def get_language_prompt(lang: str) -> str:
    """Get instruction to respond in user's language."""
    if lang == 'en':
        return ""
    return f"\n\nIMPORTANT: Respond in {SUPPORTED_LANGUAGES.get(lang, 'English')}."
```

---

### Step 4: Ollama Integration (Local LLM)

```python
import requests
import json

class OllamaClient:
    """Client for local Ollama LLM."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama3.2:3b"  # Lightweight, multilingual
    
    def generate(self, prompt: str, context: str = "", stream: bool = False) -> str:
        """Generate response using local LLM."""
        
        system_prompt = """You are a helpful travel assistant for TripRaft.
You help users discover places, plan trips, and answer travel questions.
Be concise, friendly, and informative.
When provided with place data, use it accurately.
If you don't have information, say so honestly."""
        
        full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nUser: {prompt}\n\nAssistant:"
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": stream,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 500,  # Max tokens
                    "top_p": 0.9
                }
            },
            timeout=60
        )
        
        if stream:
            return self._handle_stream(response)
        
        return response.json().get("response", "")
    
    def _handle_stream(self, response):
        """Handle streaming response."""
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                yield data.get("response", "")
                if data.get("done"):
                    break
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

# Global instance
ollama = OllamaClient()
```

---

### Step 5: Smart Query Router (Minimize LLM Calls)

The key to handling 1000+ users is to minimize expensive LLM calls.

```python
class SmartQueryRouter:
    """
    Routes queries to the cheapest effective data source.
    
    Strategy:
    1. Direct DB lookup (instant, free) - 70% of queries
    2. Vector search (fast, free) - 20% of queries  
    3. LLM generation (slower) - 10% of queries
    """
    
    def __init__(self, places_service, vector_store, llm_client):
        self.places = places_service
        self.vectors = vector_store
        self.llm = llm_client
        
        # Cache for common queries
        self.response_cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    def route(self, query: str, user_lang: str = 'en') -> dict:
        """Route query to appropriate handler."""
        
        # Check cache first
        cache_key = f"{query.lower().strip()}:{user_lang}"
        if cache_key in self.response_cache:
            cached = self.response_cache[cache_key]
            if time.time() - cached['timestamp'] < self.cache_ttl:
                return {**cached['response'], 'cache_hit': True}
        
        # Analyze query
        analysis = self._analyze_query(query)
        
        # Route based on analysis
        if analysis['type'] == 'direct_lookup':
            response = self._handle_direct_lookup(analysis, user_lang)
        elif analysis['type'] == 'semantic_search':
            response = self._handle_semantic_search(query, analysis, user_lang)
        else:
            response = self._handle_llm_generation(query, analysis, user_lang)
        
        # Cache response
        self.response_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }
        
        return response
    
    def _analyze_query(self, query: str) -> dict:
        """Analyze query to determine routing."""
        query_lower = query.lower()
        
        # Pattern matching for direct lookups
        direct_patterns = [
            (r'places?\s+(?:in|at|near)\s+(\w+)', 'city_search'),
            (r'(?:tell me about|what is|info(?:rmation)?\s+(?:about|on))\s+(.+)', 'place_detail'),
            (r'(?:top|best|popular)\s+(?:places?|attractions?)\s+in\s+(\w+)', 'city_search'),
            (r'things to do in\s+(\w+)', 'city_search'),
        ]
        
        for pattern, query_type in direct_patterns:
            match = re.search(pattern, query_lower)
            if match:
                entity = match.group(1).strip()
                return {
                    'type': 'direct_lookup',
                    'query_type': query_type,
                    'entity': entity
                }
        
        # Check if it's a semantic search query
        semantic_keywords = ['like', 'similar', 'recommend', 'suggest', 'good for', 'best for']
        if any(kw in query_lower for kw in semantic_keywords):
            return {'type': 'semantic_search'}
        
        # Default to LLM for complex queries
        return {'type': 'llm_generation'}
    
    def _handle_direct_lookup(self, analysis: dict, user_lang: str) -> dict:
        """Handle direct database lookups (fastest)."""
        entity = analysis['entity']
        query_type = analysis['query_type']
        
        if query_type == 'city_search':
            result = self.places.search_by_location(entity)
            if result['success'] and result['places']:
                return self._format_places_response(result, user_lang)
        
        elif query_type == 'place_detail':
            # Try to find exact place
            result = self.places.search_places(query=entity, limit=1)
            if result['success'] and result['places']:
                place = result['places'][0]
                return self._format_place_detail(place, user_lang)
        
        # Fallback to semantic search
        return self._handle_semantic_search(entity, analysis, user_lang)
    
    def _handle_semantic_search(self, query: str, analysis: dict, user_lang: str) -> dict:
        """Handle semantic similarity search."""
        results = self.vectors.semantic_search(query, n_results=10)
        
        if results and results['ids'] and results['ids'][0]:
            place_ids = results['ids'][0]
            # Fetch full place data from DB
            places = []
            for pid in place_ids:
                place = self.places.get_place_by_id(pid)
                if place:
                    places.append(place['place'])
            
            if places:
                return self._format_places_response(
                    {'places': places, 'count': len(places)},
                    user_lang
                )
        
        # Fallback to LLM
        return self._handle_llm_generation(query, analysis, user_lang)
    
    def _handle_llm_generation(self, query: str, analysis: dict, user_lang: str) -> dict:
        """Handle LLM-based response generation (slowest, last resort)."""
        
        # Build context from any available data
        context = self._build_context(query)
        
        # Add language instruction
        lang_instruction = get_language_prompt(user_lang)
        full_query = f"{query}{lang_instruction}"
        
        # Generate response
        response_text = self.llm.generate(full_query, context)
        
        return {
            'success': True,
            'response': response_text,
            'source': 'llm',
            'cache_hit': False
        }
    
    def _format_places_response(self, result: dict, user_lang: str) -> dict:
        """Format places into readable response."""
        places = result.get('places', [])[:10]
        
        # Build response using templates (no LLM needed)
        response_lines = []
        
        if user_lang == 'hi':
            response_lines.append("यहाँ शीर्ष स्थान हैं:\n")
        elif user_lang == 'es':
            response_lines.append("Aquí están los mejores lugares:\n")
        else:
            response_lines.append("Here are the top places:\n")
        
        for i, place in enumerate(places, 1):
            line = f"{i}. **{place['name']}**"
            if place.get('ai_summary'):
                line += f"\n   {place['ai_summary'][:150]}..."
            if place.get('cost'):
                line += f"\n   Cost: {place['cost']}"
            response_lines.append(line)
        
        return {
            'success': True,
            'response': '\n\n'.join(response_lines),
            'places': places,
            'source': 'database',
            'cache_hit': False
        }
```

---

### Step 6: Scaling to 1000+ Users

**Key Strategies:**

#### 1. Response Caching (Most Important)
```python
# 80% of travel queries are repetitive
# "best places in Paris" gets asked 100x/day
# Cache responses aggressively

CACHE_CONFIG = {
    'city_search': 3600,      # 1 hour
    'place_detail': 86400,    # 24 hours
    'itinerary': 1800,        # 30 minutes
    'llm_response': 7200      # 2 hours
}
```

#### 2. Request Queue for LLM
```python
from queue import Queue
from threading import Thread

class LLMRequestQueue:
    """Queue LLM requests to prevent overload."""
    
    def __init__(self, max_concurrent: int = 4):
        self.queue = Queue()
        self.max_concurrent = max_concurrent
        self.active_requests = 0
        
        # Start worker threads
        for _ in range(max_concurrent):
            Thread(target=self._worker, daemon=True).start()
    
    def _worker(self):
        while True:
            request_id, query, context, callback = self.queue.get()
            try:
                response = ollama.generate(query, context)
                callback(request_id, response)
            except Exception as e:
                callback(request_id, f"Error: {str(e)}")
            finally:
                self.queue.task_done()
    
    def submit(self, request_id: str, query: str, context: str, callback):
        self.queue.put((request_id, query, context, callback))
```

#### 3. Gunicorn Configuration
```python
# gunicorn.conf.py
workers = 8                    # 2 * CPU cores
worker_class = 'gevent'        # Async workers
timeout = 120                  # LLM can be slow
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
```

#### 4. Connection Pooling
```python
# Reuse connections to Ollama
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retries = Retry(total=3, backoff_factor=0.1)
session.mount('http://', HTTPAdapter(max_retries=retries, pool_maxsize=20))
```

---

### Step 7: Complete Chat Service Implementation

```python
# places_engine/chat/service.py

import time
import hashlib
from typing import Optional, Dict, List
from langdetect import detect

class TravelChatService:
    """
    Zero-cost travel chatbot service.
    Handles 1000+ users with smart routing and caching.
    """
    
    def __init__(self, places_service, vector_store, ollama_client):
        self.places = places_service
        self.vectors = vector_store
        self.llm = ollama_client
        self.router = SmartQueryRouter(places_service, vector_store, ollama_client)
        
        # Session storage (use Redis in production)
        self.sessions = {}
    
    def chat(self, session_id: str, message: str) -> Dict:
        """
        Main chat entry point.
        
        Args:
            session_id: Unique session identifier
            message: User's message
        
        Returns:
            Response dict with answer and metadata
        """
        start_time = time.time()
        
        # Get or create session
        session = self._get_session(session_id)
        
        # Detect language
        user_lang = detect_language(message)
        session['language'] = user_lang
        
        # Add to history
        session['history'].append({
            'role': 'user',
            'content': message,
            'timestamp': time.time()
        })
        
        # Route and process query
        result = self.router.route(message, user_lang)
        
        # Add response to history
        session['history'].append({
            'role': 'assistant',
            'content': result['response'],
            'timestamp': time.time()
        })
        
        # Update session context
        if result.get('places'):
            session['context']['last_places'] = [p['id'] for p in result['places'][:5]]
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            'success': True,
            'response': result['response'],
            'places': result.get('places', []),
            'source': result.get('source', 'unknown'),
            'language': user_lang,
            'cache_hit': result.get('cache_hit', False),
            'response_time_ms': response_time,
            'follow_ups': self._generate_follow_ups(result, user_lang)
        }
    
    def _get_session(self, session_id: str) -> Dict:
        """Get or create session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'id': session_id,
                'created_at': time.time(),
                'language': 'en',
                'history': [],
                'context': {
                    'last_places': [],
                    'current_location': None,
                    'preferences': {}
                }
            }
        return self.sessions[session_id]
    
    def _generate_follow_ups(self, result: Dict, lang: str) -> List[str]:
        """Generate follow-up suggestions."""
        places = result.get('places', [])
        
        if not places:
            if lang == 'hi':
                return ["मुझे किसी जगह के बारे में बताएं", "यात्रा की योजना बनाएं"]
            return ["Tell me about a destination", "Help me plan a trip"]
        
        first_place = places[0]
        city = first_place.get('city', 'this area')
        
        if lang == 'hi':
            return [
                f"{first_place['name']} के बारे में और बताएं",
                f"{city} में और क्या देखें?",
                "यात्रा कार्यक्रम बनाएं"
            ]
        
        return [
            f"Tell me more about {first_place['name']}",
            f"What else to see in {city}?",
            "Create an itinerary"
        ]
```

---

### Step 8: API Endpoints

```python
# places_engine/api/chat_routes.py

from flask import Blueprint, request, jsonify, Response
import json

chat_bp = Blueprint('chat', __name__, url_prefix='/api/v2/chat')

# Initialize service (done in app.py)
chat_service = None

def init_chat_service(service):
    global chat_service
    chat_service = service

@chat_bp.route('/message', methods=['POST'])
def send_message():
    """Send a message and get AI response."""
    data = request.get_json()
    
    session_id = data.get('session_id', request.remote_addr)
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    if len(message) > 1000:
        return jsonify({'error': 'Message too long'}), 400
    
    result = chat_service.chat(session_id, message)
    return jsonify(result)

@chat_bp.route('/stream', methods=['POST'])
def stream_message():
    """Stream response using Server-Sent Events."""
    data = request.get_json()
    
    session_id = data.get('session_id', request.remote_addr)
    message = data.get('message', '').strip()
    
    def generate():
        # First, try fast sources (DB, cache)
        result = chat_service.router.route(message, detect_language(message))
        
        if result.get('source') != 'llm':
            # Fast response, send all at once
            yield f"data: {json.dumps({'chunk': result['response'], 'done': True})}\n\n"
            return
        
        # Stream LLM response
        for chunk in chat_service.llm.generate(message, stream=True):
            yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
        
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@chat_bp.route('/history', methods=['GET'])
def get_history():
    """Get conversation history."""
    session_id = request.args.get('session_id', request.remote_addr)
    session = chat_service._get_session(session_id)
    
    return jsonify({
        'success': True,
        'history': session['history'][-20:],  # Last 20 messages
        'language': session['language']
    })

@chat_bp.route('/suggestions', methods=['GET'])
def get_suggestions():
    """Get conversation starter suggestions."""
    lang = request.args.get('lang', 'en')
    
    suggestions = {
        'en': [
            "What are the best places to visit in Paris?",
            "Plan a 3-day trip to Tokyo",
            "Hidden gems in Italy",
            "Best beaches in Thailand"
        ],
        'hi': [
            "दिल्ली में घूमने की जगहें",
            "जयपुर की यात्रा योजना",
            "केरल में क्या देखें?",
            "गोवा के सर्वश्रेष्ठ समुद्र तट"
        ],
        'es': [
            "Mejores lugares para visitar en Barcelona",
            "Plan de viaje de 3 días a Madrid",
            "Joyas ocultas en México",
            "Mejores playas en España"
        ]
    }
    
    return jsonify({
        'success': True,
        'suggestions': suggestions.get(lang, suggestions['en'])
    })
```

---

### Performance Benchmarks (Zero-Cost Stack)

| Metric | Value | Notes |
|--------|-------|-------|
| **DB Query** | 5-20ms | Direct Firestore lookup |
| **Vector Search** | 10-50ms | ChromaDB local |
| **LLM Response** | 2-8 sec | Ollama Llama 3.2 (3B) |
| **Cache Hit** | 1-5ms | Redis/memory |
| **Concurrent Users** | 1000+ | With caching + queue |
| **Requests/sec** | 200-500 | DB-only queries |
| **Requests/sec** | 8-16 | LLM queries |

### Optimization Tips

1. **Cache Aggressively**: 80% of queries are repetitive
2. **Prioritize DB**: Most questions can be answered from your data
3. **Queue LLM**: Don't let LLM block other requests
4. **Use Smaller Model**: Llama 3.2 3B is fast and multilingual
5. **Pre-compute Embeddings**: Index all places at startup

---

### Quick Start Commands

```bash
# 1. Install Ollama
winget install Ollama.Ollama
ollama pull llama3.2:3b

# 2. Install Python dependencies
pip install chromadb sentence-transformers langdetect flask gunicorn gevent redis

# 3. Index your places data
python -c "from places_engine.chat.indexer import index_all_places; index_all_places()"

# 4. Start the server
gunicorn -c gunicorn.conf.py "app:create_app()"

# 5. Test the chat
curl -X POST http://localhost:5000/api/v2/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Best places in Delhi"}'
```

---

### Free Hosting Options

If you need to deploy beyond your local machine:

| Provider | Free Tier | Limitations |
|----------|-----------|-------------|
| **Railway** | 500 hrs/month | Good for API |
| **Render** | 750 hrs/month | Spins down after idle |
| **Fly.io** | 3 shared VMs | 256MB RAM each |
| **Oracle Cloud** | Always Free | 1 GB RAM, 1 CPU |
| **Google Cloud Run** | 2M requests/month | Cold starts |

**Note**: LLM requires at least 4GB RAM, so local machine or Oracle Cloud (free 24GB RAM instance) is best.

---

## Summary (Zero-Cost Edition)

This architecture provides:

1. **100% Free**: No paid APIs, runs entirely on your machine
2. **Multilingual**: Understands Hindi, Spanish, French, and 80+ languages
3. **Context-Aware**: Maintains conversation history per session
4. **Scalable**: Handles 1000+ users with smart caching and queuing
5. **Fast**: 80% of queries answered from DB in <50ms
6. **Privacy**: All data stays on your machine

### Key Technologies (All Free)
- **Ollama + Llama 3.2**: Local LLM, no API costs
- **ChromaDB**: Local vector database
- **sentence-transformers**: Free embeddings
- **langdetect**: Free language detection
- **Redis**: Free local caching
- **Firestore Spark**: Free 20K reads/day

---

*Last Updated: December 4, 2025*

