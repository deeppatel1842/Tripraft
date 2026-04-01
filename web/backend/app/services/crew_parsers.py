"""
Crew Intent Classifier & Entity Extractor — Tiered parsing for @crew commands.

Tier 1: Pure regex for unambiguous, fully-specified commands (confidence=1.0).
Tier 2: Partial regex match + gemma3 LLM extraction for incomplete commands (confidence=0.7).

Input truncated to CREW_MAX_INPUT_CHARS before any parsing (ReDoS prevention).
All patterns compiled once at module load.
"""
import json
import logging
import re
from typing import Any, Dict, List, Tuple

from app.core.config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response types for the Crew agent card system
# ---------------------------------------------------------------------------
RESPONSE_QUESTION_CARD = 'question_card'
RESPONSE_CONFIRMATION_CARD = 'confirmation_card'
RESPONSE_PLACE_CARD = 'place_card'
RESPONSE_SUCCESS_TEXT = 'success_text'
RESPONSE_ERROR_TEXT = 'error_text'

# ---------------------------------------------------------------------------
# Intent constants
# ---------------------------------------------------------------------------
INTENT_CREATE_POLL = 'create_poll'
INTENT_CREATE_CHECKLIST = 'create_checklist'
INTENT_ADD_PLACE = 'add_place'
INTENT_CREATE_EXPENSE = 'create_expense'
INTENT_DELETE_ITEM = 'delete_item'
INTENT_SCHEDULE_PLACE = 'schedule_place'
INTENT_EXPORT = 'export'
INTENT_UNKNOWN = 'unknown'

# ---------------------------------------------------------------------------
# Complexity scores per intent (used for Phase B/C routing)
# ---------------------------------------------------------------------------
COMPLEXITY_SCORES: Dict[str, float] = {
    INTENT_CREATE_POLL: 0.2,
    INTENT_CREATE_CHECKLIST: 0.1,
    INTENT_ADD_PLACE: 0.3,
    INTENT_CREATE_EXPENSE: 0.3,
    INTENT_DELETE_ITEM: 0.2,
    INTENT_SCHEDULE_PLACE: 0.3,
    INTENT_EXPORT: 0.1,
    INTENT_UNKNOWN: 0.5,
}

# ---------------------------------------------------------------------------
# Tier 1 — Full regex patterns (all fields present, no LLM needed)
# Compiled once at module load. Kept simple to avoid ReDoS.
# ---------------------------------------------------------------------------

# "@crew create poll: Where to eat? Options: Viva Panaji, Ritz Classic"
_POLL_FULL = re.compile(
    r'(?:create|make|start|new)\s+(?:a\s+)?poll\s*[:\-]?\s*'
    r'(?P<question>.+?)\s*'
    r'(?:options?\s*[:\-]?\s*)(?P<options>.+)',
    re.IGNORECASE,
)

# "@crew create poll" / "@crew make a poll" (no question/options)
_POLL_PARTIAL = re.compile(
    r'(?:create|make|start|new)\s+(?:a\s+)?poll\b',
    re.IGNORECASE,
)

# "@crew add checklist: pack bags, book flights, buy sunscreen"
_CHECKLIST_FULL = re.compile(
    r'(?:add|create|make|start|new)\s+(?:a\s+)?checklist\s*[:\-]?\s*(?P<items>.+)',
    re.IGNORECASE,
)

# "@crew add checklist" (no items)
_CHECKLIST_PARTIAL = re.compile(
    r'(?:add|create|make|start|new)\s+(?:a\s+)?checklist\b',
    re.IGNORECASE,
)

# "@crew add place Taj Mahal"
_PLACE_FULL = re.compile(
    r'add\s+place\s+(?P<place_name>.+)',
    re.IGNORECASE,
)

# "@crew add place" (no name)
_PLACE_PARTIAL = re.compile(
    r'add\s+place\b',
    re.IGNORECASE,
)

# "@crew 1500 for dinner split equally" or "@crew add expense 1500 dinner equal"
_EXPENSE_FULL = re.compile(
    r'(?:add\s+expense\s+)?'
    r'(?P<amount>\d+(?:\.\d{1,2})?)\s+'
    r'(?:for\s+)?(?P<description>[a-zA-Z0-9\s]+?)\s+'
    r'(?:split\s+)?(?P<split_type>equal(?:ly)?|exact|percentage|shares)',
    re.IGNORECASE,
)

# "@crew add expense" (no details) or just a bare amount
_EXPENSE_PARTIAL = re.compile(
    r'(?:add|create|make|new|log)\s+(?:an?\s+)?expense\b|^\s*\d+(?:\.\d{1,2})?\s*$',
    re.IGNORECASE,
)

# "@crew delete poll Where to eat" or "@crew remove checklist pack bags"
_DELETE_FULL = re.compile(
    r'(?:delete|remove)\s+(?P<entity_type>poll|checklist|place|expense)\s+(?P<search_text>.+)',
    re.IGNORECASE,
)

# Reverse: "@crew delete the kerry park place" — entity_type at end
_DELETE_FULL_REV = re.compile(
    r'(?:delete|remove)\s+(?:the\s+)?(?P<search_text>.+?)\s+(?P<entity_type>poll|checklist|place|expense)\s*$',
    re.IGNORECASE,
)

# "@crew delete poll" (no target)
_DELETE_PARTIAL = re.compile(
    r'(?:delete|remove)\s+(?:the\s+)?(?P<entity_type>poll|checklist|place|expense)\b',
    re.IGNORECASE,
)

# "@crew export pdf" / "@crew export calendar"
_EXPORT = re.compile(
    r'export\s+(?P<format>pdf|calendar|csv)',
    re.IGNORECASE,
)

# Schedule patterns — "@crew schedule kerry park to april 2nd 10am"
# "@crew move gas works park to tomorrow 3pm"
# "@crew reschedule pike place market to dec 15 2pm"
_SCHEDULE_FULL = re.compile(
    r'\b(?:schedule|reschedule|move)\s+(?P<place_name>.+?)\s+'
    r'(?:to|on|for)\s+(?P<datetime_raw>.+)',
    re.IGNORECASE,
)

# "@crew schedule kerry park" (no date/time)
_SCHEDULE_PARTIAL = re.compile(
    r'\b(?:schedule|reschedule|move)\s+(?:the\s+)?(?P<place_name>[a-zA-Z][\w\s]+?)(?:\s*$)',
    re.IGNORECASE,
)


def _strip_mention(content: str) -> str:
    """Remove @crew mention and leading/trailing whitespace."""
    return re.sub(r'@crew\s*', '', content, flags=re.IGNORECASE).strip()


def _truncate(content: str) -> str:
    """Truncate input to CREW_MAX_INPUT_CHARS for ReDoS prevention."""
    max_chars = Config.CREW_MAX_INPUT_CHARS
    return content[:max_chars] if len(content) > max_chars else content


def _parse_option_list(raw: str) -> List[str]:
    """Split comma or semicolon-separated options, strip whitespace, dedupe."""
    items = re.split(r'[,;]', raw)
    seen = set()
    result = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            result.append(cleaned)
    return result


class CrewParsers:
    """
    Stateless intent classifier and entity extractor for @crew commands.

    Usage:
        intent, entities, confidence = CrewParsers.classify(content)
    """

    @staticmethod
    def classify(content: str) -> Tuple[str, Dict[str, Any], float]:
        """
        Classify the @crew command and extract entities.

        Returns:
            (intent, entities, confidence)
            - confidence 1.0 = regex-only, all fields present
            - confidence 0.7 = partial match, needs LLM or follow-up
        """
        cleaned = _truncate(_strip_mention(content))
        if not cleaned:
            return INTENT_UNKNOWN, {}, 0.0

        # --- Tier 1: Full regex matches (confidence=1.0) ---

        match = _POLL_FULL.search(cleaned)
        if match:
            question = match.group('question').rstrip('?').strip()
            options = _parse_option_list(match.group('options'))
            if question and len(options) >= 2:
                return INTENT_CREATE_POLL, {
                    'question': question,
                    'options': options,
                }, 1.0

        match = _CHECKLIST_FULL.search(cleaned)
        if match:
            items = _parse_option_list(match.group('items'))
            if items:
                return INTENT_CREATE_CHECKLIST, {'items': items}, 1.0

        match = _PLACE_FULL.search(cleaned)
        if match:
            place_name = match.group('place_name').strip()
            if place_name:
                return INTENT_ADD_PLACE, {'place_name': place_name}, 1.0

        match = _EXPENSE_FULL.search(cleaned)
        if match:
            split_raw = match.group('split_type').lower()
            split_type = 'equal' if split_raw.startswith('equal') else split_raw
            return INTENT_CREATE_EXPENSE, {
                'amount': float(match.group('amount')),
                'description': match.group('description').strip(),
                'split_type': split_type,
            }, 1.0

        match = _DELETE_FULL.search(cleaned)
        if match:
            return INTENT_DELETE_ITEM, {
                'entity_type': match.group('entity_type').lower(),
                'search_text': match.group('search_text').strip(),
            }, 1.0

        match = _DELETE_FULL_REV.search(cleaned)
        if match:
            return INTENT_DELETE_ITEM, {
                'entity_type': match.group('entity_type').lower(),
                'search_text': match.group('search_text').strip(),
            }, 1.0

        match = _EXPORT.search(cleaned)
        if match:
            return INTENT_EXPORT, {
                'format': match.group('format').lower(),
            }, 1.0

        match = _SCHEDULE_FULL.search(cleaned)
        if match:
            place_name = match.group('place_name').strip()
            datetime_raw = match.group('datetime_raw').strip()
            if place_name and datetime_raw:
                return INTENT_SCHEDULE_PLACE, {
                    'place_name': place_name,
                    'datetime_raw': datetime_raw,
                }, 1.0

        # --- Tier 2: Partial regex matches (confidence=0.7) ---

        if _POLL_PARTIAL.search(cleaned):
            return INTENT_CREATE_POLL, {}, 0.7

        if _CHECKLIST_PARTIAL.search(cleaned):
            return INTENT_CREATE_CHECKLIST, {}, 0.7

        if _PLACE_PARTIAL.search(cleaned):
            return INTENT_ADD_PLACE, {}, 0.7

        m = _DELETE_PARTIAL.search(cleaned)
        if m:
            return INTENT_DELETE_ITEM, {
                'entity_type': m.group('entity_type').lower(),
            }, 0.7

        m = _SCHEDULE_PARTIAL.search(cleaned)
        if m:
            return INTENT_SCHEDULE_PLACE, {
                'place_name': m.group('place_name').strip(),
            }, 0.7

        if _EXPENSE_PARTIAL.search(cleaned):
            # Try to extract just the amount if present
            amount_match = re.search(r'(\d+(?:\.\d{1,2})?)', cleaned)
            entities: Dict[str, Any] = {}
            if amount_match:
                entities['amount'] = float(amount_match.group(1))
            return INTENT_CREATE_EXPENSE, entities, 0.7

        # --- No match: attempt LLM extraction in caller ---
        return INTENT_UNKNOWN, {}, 0.0

    @staticmethod
    def complexity(intent: str) -> float:
        """Return complexity score for the given intent."""
        return COMPLEXITY_SCORES.get(intent, 0.5)

    @staticmethod
    def build_extraction_prompt(content: str) -> str:
        """
        Build an Ollama prompt for structured JSON extraction.

        Used when Tier 1+2 regex fails and we need LLM to parse the user intent.
        """
        return (
            'You are a JSON extractor for a travel group planning app. '
            'Users can create polls, checklists, add places, log expenses, '
            'delete items, and schedule/reschedule places to specific dates and times. '
            'When a user mentions setting a date, time, timing, or schedule for a place, '
            'use intent "schedule_place". Fix any obvious typos in place names. '
            'Parse the user message and return ONLY valid JSON with these fields:\n'
            '{\n'
            '  "intent": one of ["create_poll", "create_checklist", "add_place", '
            '"create_expense", "delete_item", "schedule_place", "unknown"],\n'
            '  "question": string or null,\n'
            '  "options": list of strings or null,\n'
            '  "items": list of strings or null,\n'
            '  "amount": number or null,\n'
            '  "description": string or null,\n'
            '  "split_type": one of ["equal", "exact", "percentage", "shares"] or null,\n'
            '  "place_name": string or null (corrected place name),\n'
            '  "entity_type": one of ["poll", "checklist", "place", "expense"] or null,\n'
            '  "search_text": string or null,\n'
            '  "datetime_raw": string or null (normalized date/time like "april 2nd 10am")\n'
            '}\n\n'
            f'User message: "{content}"\n\n'
            'Return ONLY the JSON object, no explanation.'
        )

    @staticmethod
    def parse_llm_extraction(raw_response: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse the LLM JSON extraction response.

        Returns (intent, entities) or (INTENT_UNKNOWN, {}) on failure.
        """
        try:
            # Strip markdown code fences if present
            cleaned = raw_response.strip()
            if cleaned.startswith('```'):
                cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)

            data = json.loads(cleaned)
            if not isinstance(data, dict):
                return INTENT_UNKNOWN, {}

            intent = data.get('intent', INTENT_UNKNOWN)
            valid_intents = {
                INTENT_CREATE_POLL, INTENT_CREATE_CHECKLIST, INTENT_ADD_PLACE,
                INTENT_CREATE_EXPENSE, INTENT_DELETE_ITEM, INTENT_SCHEDULE_PLACE,
            }
            if intent not in valid_intents:
                return INTENT_UNKNOWN, {}

            # Build entities from non-null fields
            entities = {}
            field_map = {
                'question': str,
                'options': list,
                'items': list,
                'amount': (int, float),
                'description': str,
                'split_type': str,
                'place_name': str,
                'entity_type': str,
                'search_text': str,
                'datetime_raw': str,
            }
            for field, expected_type in field_map.items():
                value = data.get(field)
                if value is not None and isinstance(value, expected_type):
                    entities[field] = value

            return intent, entities

        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning('LLM extraction parse failed: %s', exc)
            return INTENT_UNKNOWN, {}
