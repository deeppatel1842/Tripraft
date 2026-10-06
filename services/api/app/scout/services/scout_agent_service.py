# Purpose: Scout Agent Service — Core logic for the @scout travel guide agent. Responsibilities:.
"""
Scout Agent Service — Core logic for the @scout travel guide agent.

Responsibilities:
  - Intent classification (rule-based, no LLM for 70%+ of queries)
  - Rate limiting (per-user, per-group, per-LLM via Redis)
  - Context building (summary-based, anonymized, never raw messages)
  - Handler dispatch (DB-first + web fallback + LLM for complex queries)
  - Response formatting with source attribution
  - Audit logging to ai_agent_logs

All methods are stateless. Database sessions passed in from caller.
"""
import logging
import re
import time
from typing import Dict, List, Optional, Tuple

import bleach
from app.core.config import Config
from app.scout.models import (VALID_PREFERENCE_KEYS, AIAgentLog,
                                  AIPreferenceProfile)
from app.trips.models import (ChatSummary, Place, Poll,
                                             TravelGroup)
from app.scout.llm.ollama_client import (OllamaClient,
                                                  OllamaUnavailable)
from app.scout.llm.output_validator import validate_llm_output
from app.scout.llm.prompt_templates import (
    friend_summary_prompt, preference_extract_prompt, scout_system_prompt,
    scout_user_prompt, travel_intent_check_prompt)
from app.places.search.web_search import (WebSearchClient,
                                                  WebSearchUnavailable)
from app.scout.services.consent_gate import ConsentGate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent patterns — compiled once at module load
# ---------------------------------------------------------------------------
_INTENT_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ('place_search', re.compile(
        r'\b(find|search|show|suggest|where|best|top|popular|nearby|good|'
        r'tell|give|info|information|about|know|describe|details|what\s+is)\b.*'
        r'\b(place|temple|beach|restaurant|cafe|hotel|museum|park|market|shop|mall|bar|club|attraction|'
        r'monument|landmark|garden|zoo|fort|church|mosque|cathedral|waterfall|lake|mountain|tower|bridge|'
        r'stadium|gallery|library|theater|theatre|ruin|castle|palace|shrine|plaza|square)s?\b',
        re.IGNORECASE,
    )),
    ('weather', re.compile(
        r'\b(weather|rain|temperature|climate|hot|cold|humid|snow|forecast|sunny|monsoon)\b',
        re.IGNORECASE,
    )),
    ('visa', re.compile(
        r'\b(visa|passport|document|entry\s*requirements?|immigration|permit)s?\b',
        re.IGNORECASE,
    )),
    ('flight_range', re.compile(
        r'\b(flight|fly|airline|airfare|plane|airport)s?\b',
        re.IGNORECASE,
    )),
    ('hotel_range', re.compile(
        r'\b(hotel|stay|accommodation|hostel|resort|airbnb|booking|lodge)s?\b',
        re.IGNORECASE,
    )),
    ('transport', re.compile(
        r'\b(transport|bus|train|cab|taxi|drive|metro|tram|ferry|uber|rickshaw)s?\b',
        re.IGNORECASE,
    )),
    ('budget_advice', re.compile(
        r'\b(budget|cost|afford|expensive|cheap|price|spend|money)\b',
        re.IGNORECASE,
    )),
    ('preference_update', re.compile(
        r'\b(I am|I\'m|I prefer|I like|I love|I hate|I don\'t like|I can\'t eat|I need)\b',
        re.IGNORECASE,
    )),
    ('preference_summary', re.compile(
        r'\b(what does everyone|group preference|who wants|consensus|everyone like|'
        r'what do we|team preference|group wants)\b',
        re.IGNORECASE,
    )),
    ('recommendation', re.compile(
        r'\b(recommend|what should we|help decide|best option|suggest me|'
        r'any idea|what do you think|opinion)\b',
        re.IGNORECASE,
    )),
    ('redirect_crew', re.compile(
        r'\b(plan|itinerary|schedule|checklist|poll|expense|split|vote|task)\b',
        re.IGNORECASE,
    )),
    ('greeting', re.compile(
        r'\b(who\s+are\s+you|what\s+are\s+you|what\s+can\s+you\s+do|'
        r'hello|hey|hi|introduce|help|what\s+is\s+scout|about\s+you)\b',
        re.IGNORECASE,
    )),
]

# Travel keywords to detect off-topic queries
_TRAVEL_KEYWORDS = re.compile(
    r'\b(travel|trip|tour|visit|visiting|destination|hotel|flight|visa|weather|'
    r'restaurant|cafe|temple|beach|museum|budget|transport|taxi|train|'
    r'city|country|place|attraction|food|eat|cuisine|dish|drink|try|taste|'
    r'stay|book|airport|luggage|sightseeing|itinerary|explore|wander|'
    r'currency|exchange|safety|safe|danger|crime|scam|culture|language|'
    r'guide|map|route|distance|landmark|monument|tower|bridge|palace|'
    r'park|garden|mountain|lake|waterfall|island|coast|harbor|port|'
    r'souvenir|shopping|market|nightlife|festival|local|traditional|'
    r'backpack|passport|customs|immigration|border|embassy|consulate)\b',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Origin auto-detection lookup tables
# ---------------------------------------------------------------------------
_CURRENCY_TO_COUNTRY: Dict[str, str] = {
    'INR': 'India',
    'GBP': 'United Kingdom',
    'AUD': 'Australia',
    'CAD': 'Canada',
    'SGD': 'Singapore',
    'AED': 'United Arab Emirates',
    'THB': 'Thailand',
    'JPY': 'Japan',
    'CNY': 'China',
    'MYR': 'Malaysia',
    'IDR': 'Indonesia',
    'PHP': 'Philippines',
    'VND': 'Vietnam',
    'BRL': 'Brazil',
    'MXN': 'Mexico',
    'ZAR': 'South Africa',
    'NGN': 'Nigeria',
    'KES': 'Kenya',
    'SAR': 'Saudi Arabia',
    'QAR': 'Qatar',
    'KWD': 'Kuwait',
    'BHD': 'Bahrain',
    'NZD': 'New Zealand',
    'CHF': 'Switzerland',
    'SEK': 'Sweden',
    'NOK': 'Norway',
    'DKK': 'Denmark',
    'PLN': 'Poland',
    'TRY': 'Turkey',
    'EGP': 'Egypt',
    # USD and EUR are intentionally omitted — too ambiguous (many countries use them)
}

_PHONE_PREFIX_TO_COUNTRY: Dict[str, str] = {
    '+91': 'India',
    '+44': 'United Kingdom',
    '+61': 'Australia',
    '+64': 'New Zealand',
    '+65': 'Singapore',
    '+971': 'United Arab Emirates',
    '+966': 'Saudi Arabia',
    '+974': 'Qatar',
    '+965': 'Kuwait',
    '+973': 'Bahrain',
    '+81': 'Japan',
    '+86': 'China',
    '+60': 'Malaysia',
    '+62': 'Indonesia',
    '+63': 'Philippines',
    '+84': 'Vietnam',
    '+66': 'Thailand',
    '+55': 'Brazil',
    '+52': 'Mexico',
    '+27': 'South Africa',
    '+234': 'Nigeria',
    '+254': 'Kenya',
    '+20': 'Egypt',
    '+212': 'Morocco',
    '+213': 'Algeria',
    '+33': 'France',
    '+49': 'Germany',
    '+39': 'Italy',
    '+34': 'Spain',
    '+31': 'Netherlands',
    '+46': 'Sweden',
    '+47': 'Norway',
    '+45': 'Denmark',
    '+41': 'Switzerland',
    '+43': 'Austria',
    '+48': 'Poland',
    '+90': 'Turkey',
    '+7': 'Russia',
    '+1': 'United States',
}

# PII stripping patterns for query sanitization
_PII_PATTERNS = [
    re.compile(r'@\w+'),  # @mentions
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),  # emails
    re.compile(r'\b\d{10,}\b'),  # phone numbers
]


class ScoutAgentService:
    """Stateless service for processing @scout queries in group chat."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self._ollama = ollama_client or OllamaClient()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def process(
        self,
        session,
        group_id: str,
        sender_id: str,
        message_content: str,
        redis_client=None,
    ) -> Tuple[bool, Dict]:
        """
        Process a @scout mention in group chat.

        Returns (success, result_dict) where result_dict contains:
          - response: str — the text response to post in chat
          - response_type: str — 'text' | 'place_suggestion' | 'consent_card'
          - intent: str — classified intent
        """
        start_time = time.time()

        # Feature flag check
        if not Config.FF_SCOUT_AGENT:
            return False, {'error': 'Scout agent is disabled'}

        # Rate limit check (per-user)
        if redis_client and not self._check_rate_limit(redis_client, group_id, sender_id):
            return False, {
                'response': 'You\'re asking too fast. Try again in a minute.',
                'response_type': 'text',
                'intent': 'rate_limited',
            }

        # Handle opt-in/opt-out commands (no consent needed)
        opt_result = self._handle_opt_commands(message_content)
        if opt_result:
            return True, opt_result

        # Sanitize query
        sanitized = self._sanitize_query(message_content)
        if not sanitized:
            return False, {'error': 'Empty query after sanitization'}

        # Classify intent early so consent-free intents can bypass consent gate
        intent, entities = self._classify_intent(sanitized)
        # Thread sender_id through entities so visa/flight handlers can look up
        # the user's home_country preference without changing the handler signature.
        entities['_sender_id'] = sender_id

        # LLM fallback: if no regex matched, ask the model whether the query
        # is travel-related. This catches landmarks, attractions, and
        # travel questions phrased in unexpected ways (e.g. "space needle info").
        if intent == 'off_topic':
            if self._is_travel_query(sanitized):
                intent = 'complex'

        # Intents that need no consent because they neither read nor write
        # anything about the user. 'preference_update' is deliberately absent:
        # it persists AIPreferenceProfile rows, so it must pass the gate like
        # any other data write (audit P0-10). visa / flight_range stay here
        # and degrade instead -- _get_user_origin refuses to read stored
        # preferences, phone or currency without consent (audit P1-34).
        _CONSENT_FREE = {
            'greeting', 'off_topic', 'redirect_crew',
            'weather', 'visa', 'flight_range', 'hotel_range',
            'transport', 'place_search', 'budget_advice', 'complex',
        }
        if intent in _CONSENT_FREE:
            result = self._dispatch(
                session, group_id, sender_id,
                intent, entities, sanitized, [], redis_client,
            )
            latency_ms = int((time.time() - start_time) * 1000)
            self._log_interaction(
                session, group_id, sender_id, intent, sanitized,
                result.get('response', ''), 0, latency_ms,
            )
            return True, result

        # Consent check (only for intents that access group data)
        consent = ConsentGate.check(session, group_id, sender_id)
        if consent.needs_prompt:
            return True, {
                'response': self._build_consent_card(),
                'response_type': 'consent_card',
                'intent': 'consent_prompt',
            }
        if not consent.allowed:
            return True, {
                'response': "You've opted out of Scout. Say '@scout opt in' to change your mind.",
                'response_type': 'text',
                'intent': 'consent_declined',
            }

        # Check semantic cache
        cache_hit = False
        cache_key = None
        if redis_client:
            cache_key = OllamaClient.cache_key(
                group_id, sanitized, sender_id, consent.consented_user_ids,
            )
            cached = redis_client.get_json(cache_key)
            if cached:
                cache_hit = True
                latency_ms = int((time.time() - start_time) * 1000)
                self._log_interaction(
                    session, group_id, sender_id, intent, sanitized,
                    cached.get('response', ''), 0, latency_ms, cache_hit=True,
                )
                return True, cached

        # Dispatch to handler
        try:
            result = self._dispatch(
                session, group_id, sender_id,
                intent, entities, sanitized,
                consent.consented_user_ids,
                redis_client,
            )
        except OllamaUnavailable:
            result = {
                'response': "I'm having trouble thinking right now. "
                            "Try a specific question like 'weather in Goa' and I'll check directly.",
                'response_type': 'text',
                'intent': intent,
            }

        # Log interaction
        latency_ms = int((time.time() - start_time) * 1000)
        tokens_used = result.get('tokens_used', 0)
        self._log_interaction(
            session, group_id, sender_id, intent, sanitized,
            result.get('response', ''), tokens_used, latency_ms,
            cache_hit=cache_hit, error=result.get('error'),
        )

        # Cache successful LLM responses
        if redis_client and not cache_hit and 'error' not in result:
            cache_key = cache_key or OllamaClient.cache_key(
                group_id, sanitized, sender_id, consent.consented_user_ids,
            )
            redis_client.set_json(cache_key, result, ex=3600)

        return True, result

    # ------------------------------------------------------------------
    # Intent classification
    # ------------------------------------------------------------------
    def _classify_intent(self, query: str) -> Tuple[str, Dict]:
        """
        Rule-based intent classification. O(n) pattern matching.
        Returns (intent_name, extracted_entities).
        """
        entities = self._extract_entities(query)

        for intent_name, pattern in _INTENT_PATTERNS:
            if pattern.search(query):
                return intent_name, entities

        # If no pattern matched but query is travel-related, treat as complex
        if _TRAVEL_KEYWORDS.search(query):
            return 'complex', entities

        return 'off_topic', entities

    @staticmethod
    def _extract_entities(query: str) -> Dict:
        """
        Extract location and time entities from the query using regex.
        No LLM needed — O(1) pattern match against the sanitized query text.

        Examples:
          "weather in Bali next week"  -> {location: 'Bali', time: 'next week'}
          "flights to New York"        -> {location: 'New York'}
          "visa for India"             -> {location: 'India'}
        """
        entities: Dict = {}

        # Location: capitalised word(s) after a spatial preposition
        loc_match = re.search(
            r'\b(?:in|to|at|near|for|from|around|visiting|visit)\s+'
            r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})',
            query,
        )
        if loc_match:
            entities['location'] = loc_match.group(1).strip()

        # Time reference
        time_match = re.search(
            r'\b(next\s+week|this\s+weekend|tomorrow|today|next\s+month|'
            r'january|february|march|april|may|june|july|august|'
            r'september|october|november|december|'
            r'jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b',
            query,
            re.IGNORECASE,
        )
        if time_match:
            entities['time'] = time_match.group(0).strip()

        return entities

    # ------------------------------------------------------------------
    # Handler dispatch
    # ------------------------------------------------------------------
    def _dispatch(
        self,
        session,
        group_id: str,
        sender_id: str,
        intent: str,
        entities: Dict,
        query: str,
        consented_ids: List[str],
        redis_client,
    ) -> Dict:
        """Route to the appropriate handler based on classified intent."""
        handlers = {
            'place_search': self._handle_place_search,
            'weather': self._handle_weather,
            'visa': self._handle_visa,
            'flight_range': self._handle_flight_range,
            'hotel_range': self._handle_hotel_range,
            'transport': self._handle_transport,
            'budget_advice': self._handle_budget_advice,
            'preference_summary': self._handle_preference_summary,
            'recommendation': self._handle_recommendation,
            'redirect_crew': self._handle_redirect_crew,
            'off_topic': self._handle_off_topic,
            'greeting': self._handle_greeting,
            'complex': self._handle_complex,
        }

        # preference_update needs sender_id to know whose preference to store
        if intent == 'preference_update':
            return self._handle_preference_update(
                session, group_id, sender_id, consented_ids, query, entities, redis_client,
            )

        handler = handlers.get(intent, self._handle_complex)
        return handler(session, group_id, consented_ids, query, entities, redis_client)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _handle_place_search(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Search TripRaft DB first, then SearXNG/DuckDuckGo web fallback."""
        # 1. Try TripRaft DB
        try:
            from app.places.services.place_search_service import PlaceSearchService
            service = PlaceSearchService()
            result = service.search(query=query, limit=5)

            if result.places and len(result.places) >= 3:
                places_text = '\n'.join(
                    f"- {p.get('name', p.get('place_name', 'Unknown'))}"
                    f" ({p.get('city', 'Unknown')})"
                    f" - Rating: {p.get('google_rating', 'N/A')}"
                    for p in (result.places if isinstance(result.places, list) else [])
                )
                return {
                    'response': f"Found some great spots:\n{places_text}",
                    'response_type': 'place_suggestion',
                    'intent': 'place_search',
                }
        except Exception as exc:
            logger.warning('DB place search failed: %s', exc)

        # 2. Web fallback: DuckDuckGo -> summarize as friend-style message
        try:
            web_results = WebSearchClient().search(f"{query} travel guide", max_results=3)
            if web_results:
                return self._summarize_web_results(
                    session, group_id, 'place_search', query, web_results,
                    "Couldn't find that in our database. Try [TripAdvisor](https://www.tripadvisor.com) for more options.",
                    redis_client,
                )
        except Exception as exc:
            logger.warning('Web search fallback failed: %s', exc)

        # 3. LLM fallback — use Ollama to answer from training knowledge
        return self._handle_llm_query(
            session, group_id, consented_ids, query, 'place_search', redis_client,
        )

    def _handle_weather(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Weather info via DuckDuckGo search, summarized as a friend-style reply."""
        group = session.query(TravelGroup).filter_by(id=group_id).first()
        group_dest = group.destination if group and group.destination else ''
        dest = entities.get('location', group_dest)
        dest_city = dest.split(',')[0].strip() if dest else ''
        time_ref = entities.get('time', '')
        ddg_query = f"{dest_city} weather {time_ref}".strip() if dest_city else f"{query} weather"
        fallback = (
            "Check [weather.com](https://weather.com) or "
            "[timeanddate.com](https://www.timeanddate.com/weather/) for current conditions."
        )
        try:
            results = WebSearchClient().search(ddg_query, max_results=3)
            return self._summarize_web_results(
                session, group_id, 'weather', query, results, fallback, redis_client,
            )
        except WebSearchUnavailable:
            return {'response': fallback, 'response_type': 'text', 'intent': 'weather'}
        except Exception as exc:
            logger.warning('Weather DDG search failed: %s', exc)
            return {'response': fallback, 'response_type': 'text', 'intent': 'weather'}

    def _handle_visa(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Visa requirements via DuckDuckGo search, tailored to the user's home country."""
        group = session.query(TravelGroup).filter_by(id=group_id).first()
        group_dest = group.destination if group and group.destination else ''
        dest = entities.get('location', group_dest)
        dest_city = dest.split(',')[0].strip() if dest else ''

        # Auto-detect the sender's origin country from registration data.
        # Priority: explicit preference → phone prefix → default currency.
        # No user input required.
        sender_id = entities.get('_sender_id')
        home_country = (
            self._get_user_origin(session, group_id, sender_id)
            if sender_id else None
        )

        fallback = (
            "Check [visalist.io](https://visalist.io) or your country's embassy website "
            "for up-to-date visa requirements."
        )

        # Domestic shortcut: user is already in the destination country.
        if home_country and dest and self._is_domestic(home_country, dest):
            return {
                'response': (
                    f"You're from {home_country} and {dest_city} is a domestic destination "
                    "— no visa needed! Just bring your government-issued ID."
                ),
                'response_type': 'text',
                'intent': 'visa',
            }

        # Build a targeted query when we know the user's origin.
        if home_country and dest_city:
            ddg_query = f"{home_country} passport visa requirements for {dest_city}"
        elif dest_city:
            ddg_query = f"visa requirements for visiting {dest_city}"
        else:
            ddg_query = f"{query} visa requirements"

        try:
            results = WebSearchClient().search(ddg_query, max_results=3)
            return self._summarize_web_results(
                session, group_id, 'visa', query, results, fallback, redis_client,
            )
        except WebSearchUnavailable:
            return {'response': fallback, 'response_type': 'text', 'intent': 'visa'}
        except Exception as exc:
            logger.warning('Visa DDG search failed: %s', exc)
            return {'response': fallback, 'response_type': 'text', 'intent': 'visa'}

    def _handle_flight_range(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Flight price ranges via DuckDuckGo search, tailored to the user's origin country."""
        group = session.query(TravelGroup).filter_by(id=group_id).first()
        group_dest = group.destination if group and group.destination else ''
        dest = entities.get('location', group_dest)
        dest_city = dest.split(',')[0].strip() if dest else ''
        time_ref = entities.get('time', '')

        # Auto-detect the sender's origin country from registration data.
        # Priority: explicit preference → phone prefix → default currency.
        # No user input required.
        sender_id = entities.get('_sender_id')
        home_country = (
            self._get_user_origin(session, group_id, sender_id)
            if sender_id else None
        )

        fallback = (
            "Check [Google Flights](https://flights.google.com) or "
            "[Skyscanner](https://www.skyscanner.com) for current prices."
        )

        # Domestic shortcut: no international flights needed.
        if home_country and dest and self._is_domestic(home_country, dest):
            return {
                'response': (
                    f"You're in {home_country} — {dest_city} is a domestic destination! "
                    "No international flight needed. Check [Rome2Rio](https://www.rome2rio.com) "
                    "for trains, buses, or local flights."
                ),
                'response_type': 'text',
                'intent': 'flight_range',
            }

        # Build targeted query with origin when known.
        if home_country and dest_city:
            ddg_query = f"flights from {home_country} to {dest_city} {time_ref}".strip()
        elif dest_city:
            ddg_query = f"cheapest flights to {dest_city} {time_ref}".strip()
        else:
            ddg_query = f"{query} flight prices"

        try:
            results = WebSearchClient().search(ddg_query, max_results=3)
            return self._summarize_web_results(
                session, group_id, 'flight_range', query, results, fallback, redis_client,
            )
        except WebSearchUnavailable:
            return {'response': fallback, 'response_type': 'text', 'intent': 'flight_range'}
        except Exception as exc:
            logger.warning('Flight DDG search failed: %s', exc)
            return {'response': fallback, 'response_type': 'text', 'intent': 'flight_range'}

    def _handle_hotel_range(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Hotel price ranges via DuckDuckGo search, summarized as a friend-style reply."""
        group = session.query(TravelGroup).filter_by(id=group_id).first()
        group_dest = group.destination if group and group.destination else ''
        dest = entities.get('location', group_dest)
        # Use city name only — DDG returns more precise results without state/country suffix
        dest_city = dest.split(',')[0].strip() if dest else ''
        time_ref = entities.get('time', '')
        ddg_query = f"hotels in {dest_city} {time_ref} price range".strip() if dest_city else f"{query} hotel prices"
        fallback = (
            "Check [Booking.com](https://www.booking.com) or "
            "[Agoda](https://www.agoda.com) for current hotel prices."
        )
        try:
            results = WebSearchClient().search(ddg_query, max_results=3)
            return self._summarize_web_results(
                session, group_id, 'hotel_range', query, results, fallback, redis_client,
            )
        except WebSearchUnavailable:
            return {'response': fallback, 'response_type': 'text', 'intent': 'hotel_range'}
        except Exception as exc:
            logger.warning('Hotel DDG search failed: %s', exc)
            return {'response': fallback, 'response_type': 'text', 'intent': 'hotel_range'}

    def _handle_transport(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Transport options via DuckDuckGo search, summarized as a friend-style reply."""
        group = session.query(TravelGroup).filter_by(id=group_id).first()
        group_dest = group.destination if group and group.destination else ''
        dest = entities.get('location', group_dest)
        dest_city = dest.split(',')[0].strip() if dest else ''
        ddg_query = f"how to get to {dest_city} bus train transport" if dest_city else f"{query} transport options"
        fallback = "Check [Rome2Rio](https://www.rome2rio.com) for routes and transport options."
        try:
            results = WebSearchClient().search(ddg_query, max_results=3)
            return self._summarize_web_results(
                session, group_id, 'transport', query, results, fallback, redis_client,
            )
        except WebSearchUnavailable:
            return {'response': fallback, 'response_type': 'text', 'intent': 'transport'}
        except Exception as exc:
            logger.warning('Transport DDG search failed: %s', exc)
            return {'response': fallback, 'response_type': 'text', 'intent': 'transport'}

    def _handle_budget_advice(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Budget calculation from group data."""
        group = session.query(TravelGroup).filter_by(id=group_id).first()
        if not group or not group.estimated_budget:
            return {
                'response': "No budget set for this trip yet. Ask someone to set it in group settings.",
                'response_type': 'text',
                'intent': 'budget_advice',
            }

        member_count = len([m for m in (group.members or []) if m.is_active])
        if member_count == 0:
            member_count = 1

        per_person = float(group.estimated_budget) / member_count
        currency = group.budget_currency or 'USD'

        return {
            'response': (
                f"Total budget: {currency} {float(group.estimated_budget):,.0f}\n"
                f"Members: {member_count}\n"
                f"Per person: {currency} {per_person:,.0f}\n\n"
                "(from group settings)"
            ),
            'response_type': 'text',
            'intent': 'budget_advice',
        }

    def _handle_preference_summary(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Summarize group preferences from AI preference profiles."""
        prefs = session.query(AIPreferenceProfile).filter(
            AIPreferenceProfile.group_id == group_id,
            AIPreferenceProfile.user_id.in_(consented_ids),
        ).all() if consented_ids else []

        if not prefs:
            return {
                'response': "No preference data yet. Keep chatting and I'll learn what everyone likes.",
                'response_type': 'text',
                'intent': 'preference_summary',
            }

        # Anonymize and group by key
        user_aliases = {}
        alias_counter = 0
        by_key: Dict[str, List[str]] = {}

        for p in prefs:
            uid = str(p.user_id)
            if uid not in user_aliases:
                alias_counter += 1
                user_aliases[uid] = f"Member {chr(64 + alias_counter)}"
            alias = user_aliases[uid]
            by_key.setdefault(p.preference_key, []).append(f"{alias}: {p.preference_value}")

        lines = []
        for key, entries in by_key.items():
            lines.append(f"{key.replace('_', ' ').title()}: {', '.join(entries)}")

        return {
            'response': '\n'.join(lines) + '\n\n(from chat analysis)',
            'response_type': 'text',
            'intent': 'preference_summary',
        }

    def _handle_recommendation(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """LLM-powered recommendation using group context."""
        return self._handle_llm_query(
            session, group_id, consented_ids, query, 'recommendation', redis_client,
        )

    def _handle_complex(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """
        Catch-all for travel queries that didn't match a specific intent.
        Strategy: DDG web search first (real, up-to-date info), then
        pure Ollama LLM as fallback (uses training knowledge).
        """
        try:
            web_results = WebSearchClient().search(f"{query} travel guide", max_results=3)
            if web_results:
                return self._summarize_web_results(
                    session, group_id, 'complex', query, web_results,
                    None,
                    redis_client,
                )
        except Exception as exc:
            logger.debug('Complex DDG search failed, falling back to LLM: %s', exc)

        return self._handle_llm_query(
            session, group_id, consented_ids, query, 'complex', redis_client,
        )

    def _handle_preference_update(
        self, session, group_id, sender_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Instantly capture an explicit user preference and upsert to ai_preference_profiles."""
        import json as _json
        pref_key = None
        pref_value = None

        try:
            if not self._check_llm_rate_limit(redis_client, group_id):
                # Fallback: still ack without LLM extraction
                return {'response': "Got it, I'll keep that in mind.", 'response_type': 'text', 'intent': 'preference_update'}

            prompt = preference_extract_prompt(query)
            model = self._ollama.select_model('complex')
            raw_output = self._ollama.generate(prompt=prompt, model=model, max_tokens=60)
            is_valid, cleaned = validate_llm_output(raw_output)

            if is_valid:
                try:
                    data = _json.loads(cleaned)
                    pref_key = data.get('key', '').strip().lower()
                    pref_value = data.get('value', '').strip()
                except (_json.JSONDecodeError, AttributeError):
                    if ':' in cleaned:
                        parts = cleaned.split(':', 1)
                        pref_key = parts[0].strip().lower().replace(' ', '_')
                        pref_value = parts[1].strip()

        except OllamaUnavailable:
            pass
        except Exception as exc:
            logger.warning('Preference extraction failed: %s', exc)

        if pref_key and pref_value and pref_key in VALID_PREFERENCE_KEYS:
            try:
                existing = session.query(AIPreferenceProfile).filter_by(
                    group_id=group_id,
                    user_id=sender_id,
                    preference_key=pref_key,
                ).first()
                if existing:
                    existing.preference_value = str(pref_value)[:100]
                    existing.source = 'explicit'
                    existing.confidence = 1.0
                else:
                    session.add(AIPreferenceProfile(
                        group_id=group_id,
                        user_id=sender_id,
                        preference_key=pref_key,
                        preference_value=str(pref_value)[:100],
                        source='explicit',
                        confidence=1.0,
                    ))
                session.commit()
            except Exception as exc:
                logger.warning('Preference upsert failed: %s', exc)
                session.rollback()

        return {'response': "Got it, I'll keep that in mind.", 'response_type': 'text', 'intent': 'preference_update'}

    def _summarize_web_results(
        self,
        session,
        group_id: str,
        intent: str,
        query: str,
        results: List[Dict],
        fallback_message: Optional[str],
        redis_client,
    ) -> Dict:
        """Summarize DDG search results as a casual friend-style LLM response."""
        _fallback = fallback_message or "I couldn't find specific info right now. Try [Google](https://www.google.com) for that."
        if not results:
            return {'response': _fallback, 'response_type': 'text', 'intent': intent}

        group = session.query(TravelGroup).filter_by(id=group_id).first()
        destination = group.destination if group and group.destination else 'the destination'

        # Pre-filter: keep only results that mention the destination city.
        # This prevents the LLM from summarising irrelevant results (e.g. Boston
        # hotels when the group is going to Seattle).
        dest_city = destination.split(',')[0].strip().lower()
        if dest_city and dest_city != 'the destination':
            relevant = [
                r for r in results
                if dest_city in r.get('title', '').lower()
                or dest_city in r.get('snippet', '').lower()
                or dest_city in r.get('url', '').lower()
            ]
            # Only use the filtered set if we have at least one result.
            # If the filter is too aggressive, fall back to all results.
            filtered = relevant if relevant else results

        raw = '\n\n'.join(
            f"Title: {r['title']}\nURL: {r.get('url', '')}\nSnippet: {r.get('snippet', '')}"
            for r in filtered[:3]
        )

        prompt = friend_summary_prompt(intent, query, raw, destination)

        try:
            model = self._ollama.select_model('complex')
            raw_output = self._ollama.generate(
                prompt=prompt,
                model=model,
                max_tokens=Config.OLLAMA_MAX_TOKENS,
            )
            is_valid, cleaned = validate_llm_output(raw_output)
            if is_valid:
                return {'response': cleaned, 'response_type': 'text', 'intent': intent}
        except OllamaUnavailable:
            pass
        except Exception as exc:
            logger.warning('LLM web summarization failed intent=%s: %s', intent, exc)

        return {'response': _fallback, 'response_type': 'text', 'intent': intent}

    # ------------------------------------------------------------------
    # LLM travel-intent check (fallback classifier)
    # ------------------------------------------------------------------
    def _is_travel_query(self, query: str) -> bool:
        """
        Ask Ollama 3B whether a query is travel-related.
        Called ONLY when all regex classifiers returned off_topic.
        Returns True if the model responds with 'travel', False otherwise.

        Designed to be fast: max_tokens=5, no context injected.
        On any error (Ollama down, timeout) defaults to False so Scout
        stays conservative rather than sending junk to web search.
        """
        try:
            prompt = travel_intent_check_prompt(query)
            model = self._ollama.select_model('complex')
            raw = self._ollama.generate(prompt=prompt, model=model, max_tokens=5)
            return 'travel' in raw.lower()
        except OllamaUnavailable:
            return False
        except Exception as exc:
            logger.debug('Travel intent LLM check failed: %s', exc)
            return False

    @staticmethod
    def _may_read_user_data(session, group_id: str, sender_id: str) -> bool:
        """Whether this sender has consented to Scout reading their data."""
        try:
            return bool(ConsentGate.check(session, group_id, sender_id).allowed)
        except Exception:
            logger.warning(
                'Consent check failed for user=%s group=%s; treating as not '
                'consented', sender_id, group_id, exc_info=True,
            )
            return False

    def _get_user_origin(
        self, session, group_id: str, sender_id: str
    ) -> Optional[str]:
        """
        Resolve the sender's origin country from multiple signals, in priority order:
        1. Explicit preference stored in ai_preference_profiles
           (user said 'I'm from India' — highest confidence)
        2. Phone number prefix (e.g. +91 → India, +44 → UK)
        3. Default currency on the user account (e.g. INR → India, GBP → UK)
           USD and EUR are skipped — too many countries use them.
        Returns None only when all three signals are absent or ambiguous,
        or when the sender has not consented: every signal below is personal
        data held about them, and the intents that call this are served
        without consent, so the read has to be gated rather than the intent
        (audit P1-34). The callers already degrade to a generic answer.
        No external API required — all data is already in the DB.
        """
        if not self._may_read_user_data(session, group_id, sender_id):
            return None

        # 1. Explicit preference (user stated it directly)
        try:
            pref = session.query(AIPreferenceProfile).filter_by(
                group_id=group_id,
                user_id=sender_id,
                preference_key='home_country',
            ).first()
            if pref and pref.preference_value:
                return pref.preference_value
        except Exception as exc:
            logger.debug('home_country pref lookup failed: %s', exc)

        # 2 & 3. Fall back to User registration data (phone prefix, then currency)
        try:
            from app.auth.models import User
            user = session.query(User).filter_by(id=sender_id).first()
            if user:
                # Phone prefix — most specific signal
                if user.phone:
                    phone = user.phone.strip()
                    # Try longest prefix first (e.g. +234 before +2)
                    for prefix in sorted(_PHONE_PREFIX_TO_COUNTRY, key=len, reverse=True):
                        if phone.startswith(prefix):
                            return _PHONE_PREFIX_TO_COUNTRY[prefix]
                # Default currency — reasonable signal for non-USD/EUR accounts
                if user.default_currency:
                    country = _CURRENCY_TO_COUNTRY.get(user.default_currency.upper())
                    if country:
                        return country
        except Exception as exc:
            logger.debug('User origin lookup failed: %s', exc)

        return None

    @staticmethod
    def _is_domestic(home_country: str, destination: str) -> bool:
        """
        True if the user's home country is the same as the trip destination country.
        Covers: "India" in "Goa, India", "USA" in "Seattle, Washington, USA".
        """
        return home_country.lower().strip() in destination.lower()

    def _handle_redirect_crew(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Redirect action-oriented queries to @crew agent."""
        return {
            'response': "That sounds like an action item. Use the group planner tools "
                        "(polls, checklist, itinerary) for planning and coordination.",
            'response_type': 'text',
            'intent': 'redirect_crew',
        }

    def _handle_off_topic(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Reject non-travel queries."""
        return {
            'response': "I only help with travel questions for this trip. "
                        "Ask me about places, weather, budget, food, transport, or visa info.",
            'response_type': 'text',
            'intent': 'off_topic',
        }

    def _handle_greeting(
        self, session, group_id, consented_ids, query, entities, redis_client,
    ) -> Dict:
        """Introduce Scout and list capabilities."""
        group = session.query(TravelGroup).filter_by(id=group_id).first()
        dest = group.destination if group and group.destination else 'your trip'

        return {
            'response': (
                f"Hey, I'm Scout — your travel buddy for {dest}. "
                "Ask me about weather, visa info, places to visit, flights, hotels, transport, "
                "or budget. You can also tell me your preferences (like 'I'm vegetarian') "
                "and I'll remember them for the group."
            ),
            'response_type': 'text',
            'intent': 'greeting',
        }

    # ------------------------------------------------------------------
    # LLM query helper
    # ------------------------------------------------------------------
    def _handle_llm_query(
        self,
        session,
        group_id: str,
        consented_ids: List[str],
        query: str,
        intent: str,
        redis_client,
    ) -> Dict:
        """Build context, call Ollama, validate output."""
        # Check LLM rate limit
        if redis_client and not self._check_llm_rate_limit(redis_client, group_id):
            return {
                'response': "Scout has reached its daily AI limit for this group. "
                            "Try specific questions (weather, budget) that don't need AI.",
                'response_type': 'text',
                'intent': intent,
            }

        # Build context
        context = self._build_context(session, group_id, consented_ids)

        # Build prompt
        system = scout_system_prompt(
            destination=context['destination'],
            dates=context['dates'],
            budget=context['budget'],
            member_count=context['member_count'],
            preference_summary=context['preferences'],
            poll_results=context['polls'],
            places_summary=context['places'],
        )
        user_prompt = scout_user_prompt(query)
        full_prompt = f"{system}\n\n{user_prompt}"

        # Select model
        model = self._ollama.select_model(intent)

        # Call Ollama
        raw_output = self._ollama.generate(
            prompt=full_prompt,
            model=model,
            max_tokens=Config.OLLAMA_MAX_TOKENS,
        )

        # Validate output
        is_valid, cleaned = validate_llm_output(raw_output)
        if not is_valid:
            logger.warning('LLM output rejected for group=%s intent=%s', group_id, intent)

        return {
            'response': cleaned,
            'response_type': 'text',
            'intent': intent,
            'tokens_used': len(full_prompt.split()) + len(cleaned.split()),
        }

    # ------------------------------------------------------------------
    # Context builder
    # ------------------------------------------------------------------
    def _build_context(
        self, session, group_id: str, consented_ids: List[str],
    ) -> Dict:
        """
        Assemble the context window for Scout LLM queries.
        Target: ~1,050 tokens. NEVER includes raw messages.
        """
        group = session.query(TravelGroup).filter_by(id=group_id).first()

        destination = group.destination or 'Unknown' if group else 'Unknown'
        start = group.start_date.isoformat() if group and group.start_date else 'TBD'
        end = group.end_date.isoformat() if group and group.end_date else 'TBD'
        budget_val = f"{group.budget_currency or 'USD'} {float(group.estimated_budget):,.0f}" if (
            group and group.estimated_budget
        ) else 'Not set'
        member_count = len([m for m in (group.members or []) if m.is_active]) if group else 0

        # Preference profiles (anonymized)
        prefs = session.query(AIPreferenceProfile).filter(
            AIPreferenceProfile.group_id == group_id,
            AIPreferenceProfile.user_id.in_(consented_ids),
        ).all() if consented_ids else []

        user_aliases = {}
        alias_counter = 0
        pref_lines = []
        for p in prefs:
            uid = str(p.user_id)
            if uid not in user_aliases:
                alias_counter += 1
                user_aliases[uid] = f"Member {chr(64 + alias_counter)}"
            pref_lines.append(f"{user_aliases[uid]}: {p.preference_key}={p.preference_value}")

        pref_text = '\n'.join(pref_lines) if pref_lines else 'No preferences yet.'

        # Last 2 summaries
        summaries = session.query(ChatSummary).filter_by(
            group_id=group_id,
        ).order_by(ChatSummary.created_at.desc()).limit(2).all()

        summary_text = '\n'.join(s.summary_text for s in summaries) if summaries else 'No summaries yet.'

        # Active polls (not deleted, not expired)
        polls = session.query(Poll).filter_by(
            group_id=group_id, is_deleted=False,
        ).all()
        poll_text = ', '.join(
            f"'{p.name}'" for p in polls
        ) if polls else 'No open polls.'

        # Current itinerary (top 15 places)
        places = session.query(Place).filter_by(
            group_id=group_id,
        ).order_by(Place.visit_date, Place.created_at).limit(15).all()

        place_text = ', '.join(
            f"{p.name} ({p.visit_date})" if p.visit_date else p.name
            for p in places
        ) if places else 'No places added.'

        return {
            'destination': destination,
            'dates': f"{start} to {end}",
            'budget': budget_val,
            'member_count': member_count,
            'preferences': pref_text,
            'polls': poll_text,
            'places': place_text,
            'summaries': summary_text,
        }

    # ------------------------------------------------------------------
    # Rate limiting (Redis-based)
    # ------------------------------------------------------------------
    def _check_rate_limit(self, redis_client, group_id: str, user_id: str) -> bool:
        """Check per-user (per-minute) and per-group (per-day) rate limits."""
        if not redis_client.available:
            return True  # Fail open if Redis is down

        # Per-user: N per minute
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        user_key = f"ai_rate:{user_id}:scout:{now.strftime('%Y%m%d%H%M')}"
        count = redis_client.get(user_key)
        if count is not None and int(count) >= Config.SCOUT_RATE_USER_PER_MIN:
            return False
        redis_client.set(user_key, str(int(count or 0) + 1), ex=60)

        # Per-group: N per day
        group_key = f"ai_rate:{group_id}:scout:{now.strftime('%Y%m%d')}"
        g_count = redis_client.get(group_key)
        if g_count is not None and int(g_count) >= Config.SCOUT_RATE_GROUP_PER_DAY:
            return False
        redis_client.set(group_key, str(int(g_count or 0) + 1), ex=86400)

        return True

    def _check_llm_rate_limit(self, redis_client, group_id: str) -> bool:
        """Check per-group daily LLM call limit."""
        if not redis_client.available:
            return True

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        llm_key = f"ai_rate:{group_id}:llm:{now.strftime('%Y%m%d')}"
        count = redis_client.get(llm_key)
        if count is not None and int(count) >= Config.SCOUT_RATE_LLM_PER_GROUP_DAY:
            return False
        redis_client.set(llm_key, str(int(count or 0) + 1), ex=86400)

        return True

    # ------------------------------------------------------------------
    # Query sanitization
    # ------------------------------------------------------------------
    @staticmethod
    def _sanitize_query(raw: str) -> str:
        """
        Strip @mentions, PII, and HTML from user query.
        Returns cleaned plain text.
        """
        # Remove @scout mention
        cleaned = re.sub(r'@scout\b', '', raw, flags=re.IGNORECASE).strip()

        # Strip PII patterns
        for pattern in _PII_PATTERNS:
            cleaned = pattern.sub('', cleaned)

        # Strip HTML
        cleaned = bleach.clean(cleaned, tags=[], strip=True).strip()

        # Truncate to reasonable length (500 chars)
        return cleaned[:500]

    # ------------------------------------------------------------------
    # Opt-in/opt-out command detection
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_opt_commands(content: str) -> Optional[Dict]:
        """Detect '@scout opt in', '@scout opt out', '@scout forget me'."""
        lower = content.lower().strip()

        command = re.fullmatch(
            r'@scout\s+(opt\s+in|opt\s+out|forget\s+me)\s*[.!?]*',
            lower,
        )
        if not command:
            return None
        command_word = re.sub(r'\s+', ' ', command.group(1)).strip()
        if command_word == 'opt in':
            return {
                'response': 'consent_opt_in',
                'response_type': 'consent_action',
                'intent': 'opt_in',
            }
        return {
            'response': 'consent_opt_out',
            'response_type': 'consent_action',
            'intent': 'opt_out',
        }

    # ------------------------------------------------------------------
    # Consent card
    # ------------------------------------------------------------------
    @staticmethod
    def _build_consent_card() -> str:
        """Build the consent notice text shown to new users."""
        return "Scout needs your permission before it can help with that."

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------
    @staticmethod
    def _log_interaction(
        session,
        group_id: str,
        user_id: str,
        intent: str,
        query_text: str,
        response_text: str,
        tokens_used: int,
        latency_ms: int,
        cache_hit: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """Log an interaction only after the sender has consented.

        Sanitising text is not consent: query and response text are still
        personal data.  This guard is deliberately inside the logger, rather
        than only at selected call sites, so a future consent-free handler
        cannot accidentally restore the P0-10 privacy leak.
        """
        try:
            if not ConsentGate.check(session, group_id, user_id).allowed:
                logger.debug(
                    'Skipped Scout interaction log without consent: '
                    'group=%s user=%s intent=%s', group_id, user_id, intent,
                )
                return
            log = AIAgentLog(
                group_id=group_id,
                user_id=user_id,
                agent='scout',
                intent=intent,
                query_text=query_text[:500],
                response_summary=response_text[:500] if response_text else None,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                cache_hit=cache_hit,
                error=error,
            )
            session.add(log)
        except Exception as exc:
            logger.error('Failed to log AI interaction: %s', exc)
