"""
Crew Agent Service — Core orchestrator for @crew CRUD operations in group chat.

Responsibilities:
  - Dispatch messages to the correct intent handler
  - Manage multi-turn conversation state (ask follow-up questions for missing fields)
  - Execute CRUD operations via existing service layer (PollService, ChecklistService, etc.)
  - Return structured card responses (question_card, confirmation_card, place_card, etc.)

All methods are @staticmethod. No mutable instance state.
Database sessions passed in from the Celery task caller.
"""
import logging
import time
from typing import Any, Dict, Optional, Tuple

from app.core.config import Config
from app.services.crew_conversation import CrewConversation
from app.services.crew_parsers import (INTENT_ADD_PLACE,
                                       INTENT_CREATE_CHECKLIST,
                                       INTENT_CREATE_EXPENSE,
                                       INTENT_CREATE_POLL, INTENT_DELETE_ITEM,
                                       INTENT_SCHEDULE_PLACE, INTENT_UNKNOWN,
                                       RESPONSE_CONFIRMATION_CARD,
                                       RESPONSE_ERROR_TEXT,
                                       RESPONSE_PLACE_CARD,
                                       RESPONSE_QUESTION_CARD,
                                       RESPONSE_SUCCESS_TEXT, CrewParsers)

logger = logging.getLogger(__name__)

# Maximum retry count before abandoning a multi-turn flow
_MAX_RETRIES = 3

# Maps intent -> required fields for complete execution
_REQUIRED_FIELDS: Dict[str, list] = {
    INTENT_CREATE_POLL: ['question', 'options'],
    INTENT_CREATE_CHECKLIST: ['items'],
    INTENT_ADD_PLACE: ['place_name'],
    INTENT_CREATE_EXPENSE: ['amount', 'description', 'split_type'],
    INTENT_DELETE_ITEM: ['entity_type', 'search_text'],
    INTENT_SCHEDULE_PLACE: ['place_name', 'datetime_raw'],
}


def _make_result(
    response_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a standardized result dict."""
    return {
        'response_type': response_type,
        'content': content,
        'metadata': metadata or {},
    }


def _missing_fields(intent: str, entities: Dict[str, Any]) -> list:
    """Return which required fields are still missing for the given intent."""
    required = _REQUIRED_FIELDS.get(intent, [])
    return [f for f in required if f not in entities or not entities[f]]


class CrewAgentService:
    """
    Stateless orchestrator for @crew commands.

    Entry point: CrewAgentService.process(session, group_id, sender_id, message_content, redis)
    """

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    @staticmethod
    def process(
        session,
        group_id: str,
        sender_id: str,
        message_content: str,
        redis_client,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a @crew mention or a follow-up answer in group chat.

        Returns (success, result_dict) where result_dict contains:
          - response_type: question_card | confirmation_card | place_card | success_text | error_text
          - content: str — display text
          - metadata: dict — card-specific data
        """
        start = time.time()
        conv = CrewConversation(redis_client)

        try:
            # 1. Check for existing conversation state (mid-flow answer)
            existing_state = conv.get(group_id, sender_id)
            if existing_state:
                return CrewAgentService._handle_conversation_reply(
                    session, group_id, sender_id, message_content,
                    existing_state, conv, redis_client,
                )

            # 2. Fresh command — classify intent
            intent, entities, confidence = CrewParsers.classify(message_content)

            # 3. If regex failed completely, try LLM extraction
            if intent == INTENT_UNKNOWN and confidence == 0.0:
                intent, entities = CrewAgentService._try_llm_extraction(
                    message_content,
                )

            if intent == INTENT_UNKNOWN:
                return False, _make_result(
                    RESPONSE_ERROR_TEXT,
                    "Sorry, I couldn't figure out what you need. "
                    "Try things like: \"create poll\", \"add place Taj Mahal\", "
                    "\"schedule kerry park to april 2nd 10am\", \"delete checklist\", or \"add expense 500 for dinner split equal\".",
                )

            # 4. Check if all required fields are present
            missing = _missing_fields(intent, entities)
            if missing:
                # Start multi-turn conversation
                state = {
                    'intent': intent,
                    'collected_fields': entities,
                    'missing_fields': missing,
                    'retry_count': 0,
                }
                conv.set(group_id, sender_id, state)
                return True, CrewAgentService._ask_next_question(intent, missing, entities)

            # 5. All fields present — execute directly
            return CrewAgentService._dispatch(
                session, group_id, sender_id, intent, entities, conv, redis_client,
            )

        except Exception as exc:
            logger.error(
                'CrewAgentService.process failed: group=%s user=%s error=%s',
                group_id, sender_id, exc,
            )
            return False, _make_result(RESPONSE_ERROR_TEXT, 'Something went wrong. Try again.')
        finally:
            elapsed = round((time.time() - start) * 1000)
            logger.info(
                'Crew process: group=%s user=%s elapsed=%dms', group_id, sender_id, elapsed,
            )

    # ------------------------------------------------------------------
    # Conversation reply handler
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_conversation_reply(
        session,
        group_id: str,
        sender_id: str,
        message_content: str,
        state: Dict[str, Any],
        conv: CrewConversation,
        redis_client,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Handle a user's answer to a pending follow-up question."""
        intent = state['intent']
        collected = state.get('collected_fields', {})
        missing = state.get('missing_fields', [])
        retry_count = state.get('retry_count', 0)

        # Check for cancel
        cleaned = message_content.strip().lower()
        if cleaned in ('cancel', 'nevermind', 'stop', 'nvm'):
            conv.clear(group_id, sender_id)
            return True, _make_result(RESPONSE_SUCCESS_TEXT, 'Cancelled.')

        # Check for bulk field submission from multi-step card
        bulk_fields = CrewAgentService._try_parse_bulk_fields(message_content)
        if bulk_fields:
            for k, v in bulk_fields.items():
                if v is not None:
                    collected[k] = v
            remaining = _missing_fields(intent, collected)
            if not remaining:
                conv.clear(group_id, sender_id)
                return CrewAgentService._dispatch(
                    session, group_id, sender_id, intent, collected, conv, redis_client,
                )
            # Still missing some fields after bulk — fall through to normal flow
            missing = remaining

        # Fill the next missing field from the user's answer
        if missing:
            field = missing[0]
            value = CrewAgentService._parse_field_answer(field, message_content)

            if value is None:
                # Bad answer — increment retry
                retry_count += 1
                if retry_count >= _MAX_RETRIES:
                    conv.clear(group_id, sender_id)
                    return False, _make_result(
                        RESPONSE_ERROR_TEXT,
                        'Too many attempts. Start over with your @crew command.',
                    )
                state['retry_count'] = retry_count
                conv.set(group_id, sender_id, state)
                return True, CrewAgentService._ask_next_question(intent, missing, collected)

            collected[field] = value
            remaining = missing[1:]

            # Smart extraction: when user answers the poll question prompt,
            # try to extract options from the same text (e.g. "indian dinner or italian").
            # If found, skip the separate options question entirely.
            if (
                intent == INTENT_CREATE_POLL
                and field == 'question'
                and 'options' in remaining
            ):
                auto_options = CrewAgentService._try_extract_options(
                    message_content,
                )
                if auto_options:
                    collected['options'] = auto_options
                    # Build a cleaner poll question from the extracted options
                    collected['question'] = ' or '.join(auto_options)
                    remaining = [f for f in remaining if f != 'options']

            if remaining:
                # More fields needed
                state['collected_fields'] = collected
                state['missing_fields'] = remaining
                state['retry_count'] = 0
                conv.set(group_id, sender_id, state)
                return True, CrewAgentService._ask_next_question(intent, remaining, collected)

            # All fields collected — execute
            conv.clear(group_id, sender_id)
            return CrewAgentService._dispatch(
                session, group_id, sender_id, intent, collected, conv, redis_client,
            )

        conv.clear(group_id, sender_id)
        return False, _make_result(RESPONSE_ERROR_TEXT, 'Conversation expired. Start again.')

    # ------------------------------------------------------------------
    # Follow-up question builder
    # ------------------------------------------------------------------
    @staticmethod
    def _ask_next_question(
        intent: str,
        missing: list,
        collected: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a question_card for missing fields, including all field templates."""
        field = missing[0]
        question, options = _FIELD_QUESTIONS.get(
            (intent, field),
            (f'What is the {field}?', []),
        )

        # Build all_fields list for multi-step card rendering
        all_fields = []
        for f in missing:
            q, o = _FIELD_QUESTIONS.get(
                (intent, f),
                (f'What is the {f}?', []),
            )
            all_fields.append({'field': f, 'question': q, 'options': o})

        return _make_result(RESPONSE_QUESTION_CARD, question, {
            'field': field,
            'options': options,
            'intent': intent,
            'collected': collected,
            'all_fields': all_fields,
        })

    # ------------------------------------------------------------------
    # Field answer parser
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_field_answer(field: str, raw: str) -> Any:
        """Parse user's free-text answer into the expected type for a field."""
        text = raw.strip()
        if not text:
            return None

        if field == 'question':
            return text.rstrip('?').strip() or None

        if field == 'options':
            # Accept comma-separated or numbered list
            items = [i.strip() for i in text.split(',') if i.strip()]
            if len(items) < 2:
                # Try line-separated
                items = [i.strip() for i in text.split('\n') if i.strip()]
            return items if len(items) >= 2 else None

        if field == 'items':
            items = [i.strip() for i in text.split(',') if i.strip()]
            if not items:
                items = [i.strip() for i in text.split('\n') if i.strip()]
            return items or None

        if field == 'place_name':
            return text or None

        if field == 'amount':
            # Extract numeric value
            import re
            match = re.search(r'(\d+(?:\.\d{1,2})?)', text)
            if match:
                val = float(match.group(1))
                return val if val > 0 else None
            return None

        if field == 'description':
            return text or None

        if field == 'split_type':
            normalized = text.lower().strip()
            mapping = {
                'equal': 'equal', 'equally': 'equal', 'equal split': 'equal',
                'exact': 'exact', 'exact amounts': 'exact',
                'percentage': 'percentage', 'percent': 'percentage',
                'shares': 'shares',
            }
            return mapping.get(normalized)

        if field == 'entity_type':
            normalized = text.lower().strip()
            if normalized in ('poll', 'checklist', 'place', 'expense'):
                return normalized
            return None

        if field == 'search_text':
            return text or None

        if field == 'datetime_raw':
            return text or None

        return text or None

    # ------------------------------------------------------------------
    # Smart option extraction from question text
    # ------------------------------------------------------------------
    @staticmethod
    def _try_extract_options(raw: str) -> list:
        """
        Try to extract poll options from the user's question-field answer.

        Handles patterns like:
          - "indian dinner or italian"       -> ["Indian dinner", "Italian"]
          - "pizza, pasta, or sushi"         -> ["Pizza", "Pasta", "Sushi"]
          - "should we go hiking or beach"   -> ["Hiking", "Beach"]
          - "question about A or B"          -> ["A", "B"]

        Returns list of 2+ options, or empty list if extraction fails.
        """
        import re as _re

        text = raw.strip()

        # Strip common filler prefixes
        for prefix in (
            'question about', 'ask about', 'should we', 'do we want',
            'which one', 'decide between', 'vote on', 'poll about',
            'choose between',
        ):
            if text.lower().startswith(prefix):
                text = text[len(prefix):].strip()
                break

        # Strip leading "the "
        if text.lower().startswith('the '):
            text = text[4:]

        if not text:
            return []

        # Pattern: "A, B, or C" / "A or B" / "A, B, C"
        # Split on " or " and commas
        if ' or ' in text.lower() or ',' in text:
            parts = _re.split(r'\s+or\s+|,\s*', text, flags=_re.IGNORECASE)
            options = []
            for part in parts:
                cleaned = part.strip().strip('"\'').strip()
                # Strip leading "the "
                cleaned = _re.sub(r'^the\s+', '', cleaned, flags=_re.IGNORECASE).strip()
                if cleaned:
                    # Title-case each option
                    options.append(cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper())
            if len(options) >= 2:
                return options

        return []

    # ------------------------------------------------------------------
    # Bulk field parser (from multi-step card)
    # ------------------------------------------------------------------
    @staticmethod
    def _try_parse_bulk_fields(content: str) -> Optional[Dict[str, Any]]:
        """
        Parse a bulk field submission from the multi-step card.
        Format: __crew_fields__:{"field1": "val", "field2": "val"}
        Returns dict of fields or None if not a bulk submission.
        """
        import json

        prefix = '__crew_fields__:'
        if not content.strip().startswith(prefix):
            return None

        try:
            payload = json.loads(content.strip()[len(prefix):])
            if isinstance(payload, dict):
                # Parse field values using standard parser
                parsed = {}
                for field, raw_value in payload.items():
                    if isinstance(raw_value, list):
                        parsed[field] = raw_value
                    elif isinstance(raw_value, (int, float)):
                        parsed[field] = raw_value
                    else:
                        val = CrewAgentService._parse_field_answer(field, str(raw_value))
                        if val is not None:
                            parsed[field] = val
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        return None

    # ------------------------------------------------------------------
    # Dispatcher — routes to the correct CRUD handler
    # ------------------------------------------------------------------
    @staticmethod
    def _dispatch(
        session,
        group_id: str,
        sender_id: str,
        intent: str,
        entities: Dict[str, Any],
        conv: CrewConversation,
        redis_client,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Route to the correct handler based on classified intent."""
        handlers = {
            INTENT_CREATE_POLL: CrewAgentService._handle_create_poll,
            INTENT_CREATE_CHECKLIST: CrewAgentService._handle_create_checklist,
            INTENT_ADD_PLACE: CrewAgentService._handle_add_place,
            INTENT_CREATE_EXPENSE: CrewAgentService._handle_create_expense,
            INTENT_DELETE_ITEM: CrewAgentService._handle_delete_item,
            INTENT_SCHEDULE_PLACE: CrewAgentService._handle_schedule_place,
        }
        handler = handlers.get(intent)
        if not handler:
            return False, _make_result(
                RESPONSE_ERROR_TEXT,
                f'Intent "{intent}" is not supported yet.',
            )
        return handler(session, group_id, sender_id, entities, redis_client)

    # ------------------------------------------------------------------
    # CRUD Handler: Create Poll
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_create_poll(
        session, group_id: str, sender_id: str,
        entities: Dict[str, Any], redis_client,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Create a poll via PollService."""
        from app.services.poll_service import PollService

        question = entities['question']
        options = entities['options']

        success, result = PollService.create_poll(
            group_id=group_id,
            user_id=sender_id,
            name=question,
            options=options,
        )

        if not success:
            error_msg = result.get('error', 'Failed to create poll.')
            return False, _make_result(RESPONSE_ERROR_TEXT, error_msg)

        poll_data = result.get('poll', {})
        option_count = len(options)
        option_names = ', '.join(options[:5])
        return True, _make_result(
            'poll_created',
            f'Done! Created a new poll: "{question}" with {option_count} options ({option_names}). Go vote!',
            {
                'agent': 'crew',
                'intent': INTENT_CREATE_POLL,
                'poll_id': poll_data.get('id'),
                'poll': poll_data,
                'question': question,
                'option_count': option_count,
            },
        )

    # ------------------------------------------------------------------
    # CRUD Handler: Create Checklist
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_create_checklist(
        session, group_id: str, sender_id: str,
        entities: Dict[str, Any], redis_client,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Add checklist items via ChecklistService."""
        from app.services.checklist_service import ChecklistService

        items = entities['items']
        created_count = 0
        errors = []

        for item_text in items:
            success, result = ChecklistService.add_item(
                group_id=group_id,
                text=item_text,
                created_by_id=sender_id,
            )
            if success:
                created_count += 1
            else:
                errors.append(result.get('error', f'Failed to add "{item_text}"'))

        if created_count == 0:
            return False, _make_result(
                RESPONSE_ERROR_TEXT,
                'Failed to add any checklist items.',
            )

        item_names = ', '.join(items[:5])
        if len(items) > 5:
            item_names += f' (+{len(items) - 5} more)'
        msg = f'All set! Added {created_count} item{"s" if created_count != 1 else ""} to the checklist: {item_names}. Keep ticking them off!'
        if errors:
            msg += f' ({len(errors)} failed)'

        return True, _make_result(
            RESPONSE_SUCCESS_TEXT, msg,
            {
                'agent': 'crew',
                'intent': INTENT_CREATE_CHECKLIST,
                'created_count': created_count,
            },
        )

    # ------------------------------------------------------------------
    # CRUD Handler: Add Place
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_add_place(
        session, group_id: str, sender_id: str,
        entities: Dict[str, Any], redis_client,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Search for a place in travel_data_complete.db, fall back to web search.
        Then add to the group itinerary via TravelPlaceService.
        """
        from app.services.place_search_service import PlaceSearchService
        from app.services.travel_place_service import PlaceService

        place_name = entities['place_name']

        # 1. Search local DB first
        searcher = PlaceSearchService()
        search_result = searcher.search(query=place_name, limit=5)
        places = search_result.places if hasattr(search_result, 'places') else []

        if places:
            # Take the best match
            top = places[0]
            name = getattr(top, 'name', None) or top.get('name', place_name) if isinstance(top, dict) else place_name
            lat = getattr(top, 'latitude', None) or (top.get('latitude') if isinstance(top, dict) else None)
            lng = getattr(top, 'longitude', None) or (top.get('longitude') if isinstance(top, dict) else None)
            address = getattr(top, 'address', None) or (top.get('address') if isinstance(top, dict) else None)
            category = getattr(top, 'category', None) or (top.get('category') if isinstance(top, dict) else None)

            # Extract photo URL from search result (PlaceDetail.photo.thumbnail_url)
            photo_url = None
            if isinstance(top, dict):
                photo_url = top.get('photo_url')
            else:
                photo_obj = getattr(top, 'photo', None)
                if photo_obj:
                    photo_url = getattr(photo_obj, 'thumbnail_url', None)

            success, result = PlaceService.add_place(
                group_id=group_id,
                user_id=sender_id,
                name=name,
                latitude=lat,
                longitude=lng,
                address=address,
                category=category,
                photo_url=photo_url,
            )

            if not success:
                return False, _make_result(
                    RESPONSE_ERROR_TEXT,
                    result.get('error', f'Failed to add "{name}"'),
                )

            place_msg = f'Added "{name}" to the itinerary'
            if address:
                place_msg += f' at {address}'
            place_msg += '. Check it out in the places tab!'

            return True, _make_result(
                RESPONSE_PLACE_CARD,
                place_msg,
                {
                    'agent': 'crew',
                    'intent': INTENT_ADD_PLACE,
                    'place_name': name,
                    'latitude': lat,
                    'longitude': lng,
                    'address': address,
                    'photo_url': photo_url,
                    'source': 'library',
                    'place_id': result.get('id'),
                },
            )

        # 2. Web search fallback
        lat, lng, address = CrewAgentService._web_search_coordinates(place_name)
        if lat is not None and lng is not None:
            success, result = PlaceService.add_place(
                group_id=group_id,
                user_id=sender_id,
                name=place_name,
                latitude=lat,
                longitude=lng,
                address=address,
            )

            if not success:
                return False, _make_result(
                    RESPONSE_ERROR_TEXT,
                    result.get('error', f'Failed to add "{place_name}"'),
                )

            web_msg = f'Found and added "{place_name}" to the itinerary'
            if address:
                web_msg += f' at {address}'
            web_msg += '.'

            return True, _make_result(
                RESPONSE_PLACE_CARD,
                web_msg,
                {
                    'agent': 'crew',
                    'intent': INTENT_ADD_PLACE,
                    'place_name': place_name,
                    'latitude': lat,
                    'longitude': lng,
                    'address': address,
                    'source': 'web',
                    'place_id': result.get('id'),
                },
            )

        # 3. Not found anywhere
        return True, _make_result(
            RESPONSE_QUESTION_CARD,
            f'Could not find "{place_name}". Try a different name or add more details?',
            {
                'field': 'place_name',
                'options': [],
                'intent': INTENT_ADD_PLACE,
            },
        )

    # ------------------------------------------------------------------
    # CRUD Handler: Create Expense
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_create_expense(
        session, group_id: str, sender_id: str,
        entities: Dict[str, Any], redis_client,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Create an expense via ExpenseServiceSQL."""
        from app.services.expense_service import ExpenseServiceSQL

        amount = entities['amount']
        description = entities['description']
        split_type = entities.get('split_type', 'equal')

        success, result = ExpenseServiceSQL.create_expense(
            user_id=sender_id,
            group_id=int(group_id) if group_id else None,
            description=description,
            amount=amount,
            paid_by=int(sender_id),
            split_type=split_type,
        )

        if not success:
            error_msg = result.get('error', 'Failed to create expense.')
            return False, _make_result(RESPONSE_ERROR_TEXT, error_msg)

        return True, _make_result(
            RESPONSE_SUCCESS_TEXT,
            f'Logged an expense: {description} for {amount}, split {split_type} among the group.',
            {
                'agent': 'crew',
                'intent': INTENT_CREATE_EXPENSE,
                'expense_id': result.get('id'),
                'amount': amount,
                'description': description,
                'split_type': split_type,
            },
        )

    # ------------------------------------------------------------------
    # CRUD Handler: Delete Item
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_delete_item(
        session, group_id: str, sender_id: str,
        entities: Dict[str, Any], redis_client,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Fuzzy-match the target entity and return a confirmation card.
        Actual deletion happens when the user confirms via the /confirm endpoint.
        """
        import json

        entity_type = entities['entity_type']
        search_text = entities['search_text']

        # Search for matching entities
        matches = CrewAgentService._fuzzy_search_entity(
            session, group_id, entity_type, search_text,
        )

        if not matches:
            return False, _make_result(
                RESPONSE_ERROR_TEXT,
                f'No {entity_type} matching "{search_text}" found.',
            )

        if len(matches) == 1:
            # Single match — ask for confirmation
            target = matches[0]
            pending_key = f'crew:confirm:{group_id}:{sender_id}'

            if redis_client and redis_client.available:
                redis_client.set(
                    pending_key,
                    json.dumps({
                        'entity_type': entity_type,
                        'entity_id': str(target['id']),
                        'entity_name': target['name'],
                    }),
                    ex=Config.CREW_CONV_TTL,
                )

            return True, _make_result(
                RESPONSE_CONFIRMATION_CARD,
                f'Delete {entity_type} "{target["name"]}"? This cannot be undone.',
                {
                    'agent': 'crew',
                    'intent': INTENT_DELETE_ITEM,
                    'entity_type': entity_type,
                    'entity_id': str(target['id']),
                    'entity_name': target['name'],
                    'pending_key': pending_key,
                    'target_user_id': sender_id,
                },
            )

        # Multiple matches — let user pick
        options = [m['name'] for m in matches[:5]]
        return True, _make_result(
            RESPONSE_QUESTION_CARD,
            f'Found {len(matches)} matching {entity_type}s. Which one?',
            {
                'field': 'search_text',
                'options': options,
                'intent': INTENT_DELETE_ITEM,
                'collected': {'entity_type': entity_type},
            },
        )

    # ------------------------------------------------------------------
    # CRUD Handler: Schedule / Reschedule Place
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_schedule_place(
        session, group_id: str, sender_id: str,
        entities: Dict[str, Any], redis_client,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Schedule or reschedule an existing place to a new date/time.
        Uses dateutil for natural language date parsing.
        """
        from app.services.travel_place_service import PlaceService

        place_name = entities['place_name']
        datetime_raw = entities['datetime_raw']

        # 1. Fuzzy-find the place in the group itinerary
        matches = CrewAgentService._fuzzy_search_entity(
            session, group_id, 'place', place_name,
        )

        if not matches:
            return False, _make_result(
                RESPONSE_ERROR_TEXT,
                f'No place matching "{place_name}" found in your itinerary.',
            )

        if len(matches) > 1:
            options = [m['name'] for m in matches[:5]]
            return True, _make_result(
                RESPONSE_QUESTION_CARD,
                f'Found {len(matches)} matching places. Which one?',
                {
                    'field': 'place_name',
                    'options': options,
                    'intent': INTENT_SCHEDULE_PLACE,
                    'collected': {'datetime_raw': datetime_raw},
                },
            )

        target = matches[0]

        # 2. Parse the natural language date/time
        visit_date, suggested_time = CrewAgentService._parse_datetime_natural(
            datetime_raw,
        )

        if not visit_date:
            return False, _make_result(
                RESPONSE_ERROR_TEXT,
                f'Could not understand the date/time "{datetime_raw}". '
                'Try formats like "april 2nd 10am", "tomorrow 3pm", or "dec 15".',
            )

        # 3. Update the place
        update_kwargs = {}
        if suggested_time:
            update_kwargs['suggested_time'] = suggested_time

        success, result = PlaceService.update_place(
            group_id=group_id,
            place_id=str(target['id']),
            user_id=sender_id,
            visit_date=visit_date,
            **update_kwargs,
        )

        if not success:
            return False, _make_result(
                RESPONSE_ERROR_TEXT,
                result.get('error', f'Failed to schedule "{target["name"]}"'),
            )

        time_str = f' at {suggested_time}' if suggested_time else ''
        return True, _make_result(
            RESPONSE_SUCCESS_TEXT,
            f'Done! Scheduled "{target["name"]}" for {visit_date}{time_str}. Updated in the itinerary.',
            {
                'agent': 'crew',
                'intent': INTENT_SCHEDULE_PLACE,
                'place_id': str(target['id']),
                'place_name': target['name'],
                'visit_date': visit_date,
                'suggested_time': suggested_time,
            },
        )

    # ------------------------------------------------------------------
    # Helper: Natural language date/time parser
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_datetime_natural(raw: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse natural language date/time into (ISO date str, HH:MM str).

        Handles: "april 2nd 10am", "tomorrow 3pm", "dec 15", "2024-12-25 14:00"
        Returns (date_iso, time_hhmm) or (None, None) on parse failure.
        """
        import re
        from datetime import datetime as dt
        from datetime import timedelta

        text = raw.strip().lower()

        # Handle relative dates
        today = dt.now().date()
        if text.startswith('today'):
            base_date = today
            text = text.replace('today', '', 1).strip()
        elif text.startswith('tomorrow'):
            base_date = today + timedelta(days=1)
            text = text.replace('tomorrow', '', 1).strip()
        else:
            base_date = None

        # Extract time component (10am, 3:30pm, 14:00, etc.)
        time_match = re.search(
            r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b|(\d{1,2}):(\d{2})\b',
            text, re.IGNORECASE,
        )
        suggested_time = None
        if time_match:
            if time_match.group(4):
                # 24h format: 14:00
                h, m = int(time_match.group(4)), int(time_match.group(5))
            else:
                h = int(time_match.group(1))
                m = int(time_match.group(2) or 0)
                period = time_match.group(3).lower()
                if period == 'pm' and h != 12:
                    h += 12
                elif period == 'am' and h == 12:
                    h = 0
            if 0 <= h <= 23 and 0 <= m <= 59:
                suggested_time = f'{h:02d}:{m:02d}'
            # Remove matched time from text for date parsing
            text = text[:time_match.start()] + text[time_match.end():]
            text = text.strip().rstrip('at').rstrip('on').rstrip('for').strip()

        if base_date:
            return base_date.isoformat(), suggested_time

        # Try dateutil for the remaining date text
        try:
            from dateutil import parser as dateutil_parser
            parsed = dateutil_parser.parse(text, fuzzy=True, dayfirst=False)
            # If no year was specified and parsed date is in the past, bump to next year
            if parsed.date() < today and str(parsed.year) not in raw:
                parsed = parsed.replace(year=parsed.year + 1)
            return parsed.date().isoformat(), suggested_time
        except (ValueError, OverflowError):
            pass

        # Fallback: try ISO format
        iso_match = re.search(r'(\d{4}-\d{2}-\d{2})', raw)
        if iso_match:
            return iso_match.group(1), suggested_time

        return None, None

    # ------------------------------------------------------------------
    # Helper: Fuzzy search entity
    # ------------------------------------------------------------------
    @staticmethod
    def _fuzzy_search_entity(
        session, group_id: str, entity_type: str, search_text: str,
    ) -> list:
        """
        Search for entities by name using word-level ILIKE matching.
        Splits search_text into words, matches any word, then ranks by
        number of matching words. Handles typos better than exact ILIKE.
        Returns list of dicts with {id, name}.
        """
        from sqlalchemy import func, or_

        results = []
        words = [w.strip() for w in search_text.split() if len(w.strip()) >= 2]
        if not words:
            words = [search_text.strip()]

        try:
            if entity_type == 'poll':
                from app.domain.group_planner.models import Poll
                col = Poll.name
                query = session.query(Poll.id, Poll.name).filter(
                    Poll.group_id == group_id,
                    or_(*[col.ilike(f'%{w}%') for w in words]),
                ).limit(5)
                results = [{'id': str(r.id), 'name': r.name} for r in query.all()]

            elif entity_type == 'checklist':
                from app.domain.group_planner.models import ChecklistItem
                col = ChecklistItem.text
                query = session.query(ChecklistItem.id, ChecklistItem.text).filter(
                    ChecklistItem.group_id == group_id,
                    or_(*[col.ilike(f'%{w}%') for w in words]),
                ).limit(5)
                results = [{'id': str(r.id), 'name': r.text} for r in query.all()]

            elif entity_type == 'place':
                from app.domain.group_planner.models import Place
                col = Place.name
                query = session.query(Place.id, Place.name).filter(
                    Place.group_id == group_id,
                    Place.is_deleted == False,
                    or_(*[col.ilike(f'%{w}%') for w in words]),
                ).limit(5)
                results = [{'id': str(r.id), 'name': r.name} for r in query.all()]

            # Rank by number of word matches (best match first)
            if len(words) > 1 and results:
                def match_score(name):
                    lower = name.lower()
                    return sum(1 for w in words if w.lower() in lower)
                results.sort(key=lambda r: match_score(r['name']), reverse=True)

        except Exception as exc:
            logger.error('Fuzzy search failed: entity_type=%s error=%s', entity_type, exc)

        return results

    # ------------------------------------------------------------------
    # Helper: Web search for coordinates
    # ------------------------------------------------------------------
    @staticmethod
    def _web_search_coordinates(
        place_name: str,
    ) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Search the web for a place's coordinates via SearXNG/DuckDuckGo.
        Uses gemma3 to extract lat/lng from search results.

        Returns (latitude, longitude, address) or (None, None, None).
        """
        try:
            from app.infrastructure.llm.ollama_client import (
                OllamaClient, OllamaUnavailable)
            from app.infrastructure.search.web_search import (
                WebSearchClient, WebSearchUnavailable)

            web = WebSearchClient()
            results = web.search(f'{place_name} coordinates location address', max_results=3)

            if not results:
                return None, None, None

            snippets = ' | '.join(r.get('snippet', '') for r in results[:3])

            prompt = (
                'Extract the latitude, longitude, and address from these search results. '
                'Return ONLY valid JSON: {"latitude": number, "longitude": number, "address": "string"}\n'
                f'Place: {place_name}\n'
                f'Search results: {snippets[:800]}\n'
                'JSON:'
            )

            ollama = OllamaClient()
            raw = ollama.generate(
                prompt=prompt,
                model=Config.OLLAMA_MODEL_CREW,
                max_tokens=100,
            )

            import json
            import re

            cleaned = raw.strip()
            if cleaned.startswith('```'):
                cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)

            data = json.loads(cleaned)
            lat = float(data.get('latitude', 0))
            lng = float(data.get('longitude', 0))
            address = data.get('address', '')

            if -90 <= lat <= 90 and -180 <= lng <= 180 and (lat != 0 or lng != 0):
                return lat, lng, address or None

        except (WebSearchUnavailable, OllamaUnavailable) as exc:
            logger.warning('Web coordinate search unavailable: %s', exc)
        except Exception as exc:
            logger.warning('Web coordinate extraction failed: %s', exc)

        return None, None, None

    # ------------------------------------------------------------------
    # Helper: LLM intent extraction fallback
    # ------------------------------------------------------------------
    @staticmethod
    def _try_llm_extraction(content: str) -> Tuple[str, Dict[str, Any]]:
        """Attempt LLM-based intent classification when regex fails entirely."""
        try:
            from app.infrastructure.llm.ollama_client import (
                OllamaClient, OllamaUnavailable)

            prompt = CrewParsers.build_extraction_prompt(content)
            ollama = OllamaClient()
            raw = ollama.generate(
                prompt=prompt,
                model=Config.OLLAMA_MODEL_CREW,
                max_tokens=200,
            )
            return CrewParsers.parse_llm_extraction(raw)

        except OllamaUnavailable:
            logger.info('Ollama unavailable for crew LLM extraction')
        except Exception as exc:
            logger.warning('Crew LLM extraction failed: %s', exc)

        return INTENT_UNKNOWN, {}


# ---------------------------------------------------------------------------
# Question templates for multi-turn conversation
# field key -> (question_text, option_chips)
# ---------------------------------------------------------------------------
_FIELD_QUESTIONS: Dict[Tuple, Tuple[str, list]] = {
    (INTENT_CREATE_POLL, 'question'): (
        'What should the poll ask?',
        [],
    ),
    (INTENT_CREATE_POLL, 'options'): (
        'What are the options? (comma-separated, min 2)',
        ['Yes / No', 'A / B / C', 'Custom'],
    ),
    (INTENT_CREATE_CHECKLIST, 'items'): (
        'What items to add to the checklist? (comma-separated)',
        [],
    ),
    (INTENT_ADD_PLACE, 'place_name'): (
        'Which place do you want to add?',
        [],
    ),
    (INTENT_CREATE_EXPENSE, 'amount'): (
        'How much was the expense?',
        ['500', '1000', '2000', 'Custom amount'],
    ),
    (INTENT_CREATE_EXPENSE, 'description'): (
        'What was the expense for?',
        ['Food', 'Transport', 'Accommodation', 'Custom'],
    ),
    (INTENT_CREATE_EXPENSE, 'split_type'): (
        'How to split?',
        ['Equal split', 'Exact amounts', 'Percentage'],
    ),
    (INTENT_DELETE_ITEM, 'entity_type'): (
        'What do you want to delete?',
        ['Poll', 'Checklist', 'Place'],
    ),
    (INTENT_DELETE_ITEM, 'search_text'): (
        'Which one? Type the name or part of it.',
        [],
    ),
    (INTENT_SCHEDULE_PLACE, 'place_name'): (
        'Which place do you want to schedule?',
        [],
    ),
    (INTENT_SCHEDULE_PLACE, 'datetime_raw'): (
        'When should it be scheduled? (e.g. "april 2nd 10am", "tomorrow 3pm")',
        ['Tomorrow morning', 'Tomorrow afternoon', 'Custom'],
    ),
}
