"""
Crew Agent — Test Suite

Tests every layer of the @crew pipeline:
  1. Intent classification (regex Tier 1 + Tier 2 for all intents)
  2. Entity extraction (poll with options, expense with amount, etc.)
  3. Conversation state manager (Redis get/set/clear + TTL)
  4. CrewAgentService.process() — multi-turn Q&A flow
  5. Response-to-message mapping (_crew_map_response UUID safety)
  6. Full pipeline with DB session (end-to-end)

Run from web/backend/:
  python scripts/test_crew_agent.py
"""
import json
import os
import sys
import time

sys.path.insert(
    0,
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")),
)

from app.core.config import Config

# -----------------------------------------------------------------------
# Test harness
# -----------------------------------------------------------------------
_passed = 0
_failed = 0
_errors = []


def check(name, condition, detail=""):
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        msg = f" -- {detail}" if detail else ""
        _errors.append((name, detail))
        print(f"  FAIL  {name}{msg}")


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


# -----------------------------------------------------------------------
# 1. Config
# -----------------------------------------------------------------------
def test_config():
    section("1. Config")
    check("FF_CREW_AGENT is True", Config.FF_CREW_AGENT is True)
    check("CREW_AGENT_MENTION is @crew", Config.CREW_AGENT_MENTION == "@crew")
    check("CREW_SYSTEM_USER_ID set", bool(Config.CREW_SYSTEM_USER_ID))
    check("OLLAMA_MODEL_CREW set", bool(Config.OLLAMA_MODEL_CREW))
    check("CREW_CONV_TTL > 0", Config.CREW_CONV_TTL > 0)
    check("CREW_RATE_USER_PER_MIN > 0", Config.CREW_RATE_USER_PER_MIN > 0)
    check("CREW_MAX_INPUT_CHARS > 0", Config.CREW_MAX_INPUT_CHARS > 0)


# -----------------------------------------------------------------------
# 2. Intent Classification — Tier 1 (Full regex, confidence=1.0)
# -----------------------------------------------------------------------
def test_tier1_classification():
    section("2. Tier 1 — Full Regex Classification")
    from app.services.crew_parsers import (INTENT_ADD_PLACE,
                                           INTENT_CREATE_CHECKLIST,
                                           INTENT_CREATE_EXPENSE,
                                           INTENT_CREATE_POLL,
                                           INTENT_DELETE_ITEM, CrewParsers)

    # Poll with full fields
    cases = [
        (
            "@crew create poll: Where to eat? Options: Viva, Ritz",
            INTENT_CREATE_POLL,
            1.0,
            {"question": "Where to eat", "options": ["Viva", "Ritz"]},
        ),
        (
            "@crew make a poll: Best day? Options: Monday, Tuesday, Friday",
            INTENT_CREATE_POLL,
            1.0,
            {"question": "Best day", "options": ["Monday", "Tuesday", "Friday"]},
        ),
        (
            "@crew add checklist: pack bags, book flights, buy sunscreen",
            INTENT_CREATE_CHECKLIST,
            1.0,
            {"items": ["pack bags", "book flights", "buy sunscreen"]},
        ),
        (
            "@crew add place Taj Mahal",
            INTENT_ADD_PLACE,
            1.0,
            {"place_name": "Taj Mahal"},
        ),
        (
            "@crew 1500 for dinner split equally",
            INTENT_CREATE_EXPENSE,
            1.0,
            {"amount": 1500.0, "description": "dinner", "split_type": "equal"},
        ),
        (
            "@crew delete poll Where to eat",
            INTENT_DELETE_ITEM,
            1.0,
            {"entity_type": "poll", "search_text": "Where to eat"},
        ),
    ]

    for text, expected_intent, expected_conf, expected_entities in cases:
        intent, entities, conf = CrewParsers.classify(text)
        label = text[:50]
        check(
            f"[{label}] intent={expected_intent}",
            intent == expected_intent,
            f"got {intent}",
        )
        check(
            f"[{label}] conf={expected_conf}",
            conf == expected_conf,
            f"got {conf}",
        )
        for key, val in expected_entities.items():
            check(
                f"[{label}] entity.{key}",
                entities.get(key) == val,
                f"expected {val!r}, got {entities.get(key)!r}",
            )


# -----------------------------------------------------------------------
# 3. Intent Classification — Tier 2 (Partial match, confidence=0.7)
# -----------------------------------------------------------------------
def test_tier2_classification():
    section("3. Tier 2 — Partial Regex Classification")
    from app.services.crew_parsers import (INTENT_ADD_PLACE,
                                           INTENT_CREATE_CHECKLIST,
                                           INTENT_CREATE_EXPENSE,
                                           INTENT_CREATE_POLL,
                                           INTENT_DELETE_ITEM, CrewParsers)

    partial_cases = [
        ("@crew create poll", INTENT_CREATE_POLL),
        ("@crew make a poll", INTENT_CREATE_POLL),
        ("@crew start a poll", INTENT_CREATE_POLL),
        ("@crew new poll", INTENT_CREATE_POLL),
        ("@crew add checklist", INTENT_CREATE_CHECKLIST),
        ("@crew make a checklist", INTENT_CREATE_CHECKLIST),
        ("@crew add place", INTENT_ADD_PLACE),
        ("@crew add expense", INTENT_CREATE_EXPENSE),
        ("@crew log an expense", INTENT_CREATE_EXPENSE),
        ("@crew delete poll", INTENT_DELETE_ITEM),
        ("@crew remove checklist", INTENT_DELETE_ITEM),
    ]

    for text, expected_intent in partial_cases:
        intent, entities, conf = CrewParsers.classify(text)
        check(
            f"[{text}] -> {expected_intent}",
            intent == expected_intent and conf == 0.7,
            f"got intent={intent}, conf={conf}",
        )


# -----------------------------------------------------------------------
# 4. Unknown / Edge Cases
# -----------------------------------------------------------------------
def test_unknown_classification():
    section("4. Unknown & Edge Cases")
    from app.services.crew_parsers import INTENT_UNKNOWN, CrewParsers

    unknowns = [
        "@crew hello",
        "@crew what time is it",
        "@crew",
        "",
    ]
    for text in unknowns:
        intent, _, conf = CrewParsers.classify(text)
        check(
            f"[{text or '(empty)'}] -> unknown",
            intent == INTENT_UNKNOWN,
            f"got intent={intent}, conf={conf}",
        )

    # Input truncation (ReDoS prevention)
    long_input = "@crew " + "a" * 2000
    intent, _, _ = CrewParsers.classify(long_input)
    check(
        "Long input truncated safely",
        intent == INTENT_UNKNOWN,
        f"got intent={intent}",
    )


# -----------------------------------------------------------------------
# 5. Conversation State Manager (Redis)
# -----------------------------------------------------------------------
def test_conversation_state():
    section("5. Conversation State Manager")
    from app.infrastructure.cache.redis import redis_client
    from app.services.crew_conversation import CrewConversation

    if not redis_client or not redis_client.available:
        print("  SKIP  Redis not available — skipping conversation state tests")
        return

    conv = CrewConversation(redis_client)
    g = "test-group-crew"
    u = "test-user-crew"

    # Clear any leftover state
    conv.clear(g, u)

    # Initially empty
    check("get() returns None for fresh key", conv.get(g, u) is None)

    # Set and retrieve
    state = {
        "intent": "create_poll",
        "collected_fields": {"question": "Where?"},
        "missing_fields": ["options"],
        "retry_count": 0,
    }
    conv.set(g, u, state)
    retrieved = conv.get(g, u)
    check("set/get round-trip works", retrieved is not None)
    check("state intent preserved", retrieved.get("intent") == "create_poll")
    check(
        "state collected preserved",
        retrieved.get("collected_fields", {}).get("question") == "Where?",
    )

    # Clear
    conv.clear(g, u)
    check("clear removes state", conv.get(g, u) is None)


# -----------------------------------------------------------------------
# 6. CrewAgentService.process() — Multi-turn Q&A
# -----------------------------------------------------------------------
def test_agent_process():
    section("6. CrewAgentService.process() — Multi-turn Flow")
    from app.infrastructure.cache.redis import redis_client
    from app.infrastructure.db.connection import get_db
    from app.services.crew_agent_service import CrewAgentService
    from app.services.crew_conversation import CrewConversation

    redis = redis_client if redis_client and redis_client.available else None
    if not redis:
        print("  SKIP  Redis not available — skipping process tests")
        return

    group_id = "test-group-crew-flow"
    sender_id = "test-sender-crew-flow"

    # Clear any leftover conversation state
    conv = CrewConversation(redis)
    conv.clear(group_id, sender_id)

    # Step 1: "@crew make a poll" — should return question_card for 'question'
    with get_db() as session:
        success, result = CrewAgentService.process(
            session=session,
            group_id=group_id,
            sender_id=sender_id,
            message_content="@crew make a poll",
            redis_client=redis,
        )

    check("make a poll -> success", success is True)
    check(
        "make a poll -> question_card",
        result.get("response_type") == "question_card",
        f"got {result.get('response_type')}",
    )
    check(
        "make a poll -> asks for question",
        result.get("metadata", {}).get("field") == "question",
        f"got field={result.get('metadata', {}).get('field')}",
    )
    check(
        "make a poll -> content is prompt",
        "poll ask" in (result.get("content") or "").lower(),
        f"got content={result.get('content')!r}",
    )

    # Step 2: User answers the question — should ask for options next
    with get_db() as session:
        success2, result2 = CrewAgentService.process(
            session=session,
            group_id=group_id,
            sender_id=sender_id,
            message_content="Where should we eat dinner",
            redis_client=redis,
        )

    check("answer question -> success", success2 is True)
    check(
        "answer question -> still question_card (needs options)",
        result2.get("response_type") == "question_card",
        f"got {result2.get('response_type')}",
    )
    check(
        "answer question -> asks for options",
        result2.get("metadata", {}).get("field") == "options",
        f"got field={result2.get('metadata', {}).get('field')}",
    )

    # Step 3: User provides options — should execute the poll creation
    with get_db() as session:
        success3, result3 = CrewAgentService.process(
            session=session,
            group_id=group_id,
            sender_id=sender_id,
            message_content="Viva Panjim, Ritz Classic, Fisherman's Wharf",
            redis_client=redis,
        )

    # This will either succeed (success_text) or fail if no real DB group
    # Either way, the intent should have been dispatched (not another question_card for options)
    check(
        "options answer -> dispatched (not asking same question again)",
        result3.get("metadata", {}).get("field") != "options",
        f"got {result3}",
    )

    # Cleanup
    conv.clear(group_id, sender_id)


# -----------------------------------------------------------------------
# 7. Cancel mid-conversation
# -----------------------------------------------------------------------
def test_cancel_flow():
    section("7. Cancel Mid-Conversation")
    from app.infrastructure.cache.redis import redis_client
    from app.infrastructure.db.connection import get_db
    from app.services.crew_agent_service import CrewAgentService
    from app.services.crew_conversation import CrewConversation

    redis = redis_client if redis_client and redis_client.available else None
    if not redis:
        print("  SKIP  Redis not available")
        return

    group_id = "test-group-crew-cancel"
    sender_id = "test-sender-crew-cancel"
    conv = CrewConversation(redis)
    conv.clear(group_id, sender_id)

    # Start a flow
    with get_db() as session:
        CrewAgentService.process(
            session=session,
            group_id=group_id,
            sender_id=sender_id,
            message_content="@crew make a poll",
            redis_client=redis,
        )

    # Cancel
    with get_db() as session:
        success, result = CrewAgentService.process(
            session=session,
            group_id=group_id,
            sender_id=sender_id,
            message_content="cancel",
            redis_client=redis,
        )

    check("cancel -> success", success is True)
    check(
        "cancel -> success_text",
        result.get("response_type") == "success_text",
        f"got {result.get('response_type')}",
    )
    check(
        "cancel -> clears state",
        conv.get(group_id, sender_id) is None,
    )


# -----------------------------------------------------------------------
# 8. UUID safety in _crew_map_response
# -----------------------------------------------------------------------
def test_uuid_serialization():
    section("8. UUID Serialization Safety")
    import uuid

    # Simulate what gp_chat.py does
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    # Inline the function to test it independently
    def _crew_map_response(response_type, metadata, sender_id):
        base_meta = {"agent": "crew"}
        base_meta.update(metadata)
        safe_sender = str(sender_id) if sender_id is not None else None
        if response_type == "question_card":
            base_meta["target_user_id"] = safe_sender
            return "crew_question", base_meta
        if response_type == "confirmation_card":
            base_meta["target_user_id"] = safe_sender
            return "crew_confirm", base_meta
        if response_type == "place_card":
            return "crew_place", base_meta
        if response_type == "error_text":
            base_meta["target_user_id"] = safe_sender
            return "crew_error", base_meta
        return "text", base_meta

    # Test with UUID object (the bug scenario)
    uid = uuid.UUID("019d2c60-3fcb-7ce5-8883-11272ca1e5e2")
    msg_type, meta = _crew_map_response("question_card", {"intent": "create_poll"}, uid)

    check("msg_type is crew_question", msg_type == "crew_question")
    check(
        "target_user_id is str, not UUID",
        isinstance(meta["target_user_id"], str),
        f"got type={type(meta['target_user_id']).__name__}",
    )

    # Verify it's JSON serializable
    try:
        json.dumps(meta)
        check("metadata is JSON serializable", True)
    except TypeError as exc:
        check("metadata is JSON serializable", False, str(exc))

    # Test with string (normal case)
    msg_type2, meta2 = _crew_map_response("error_text", {}, "some-user-id")
    check(
        "string sender_id stays string",
        meta2["target_user_id"] == "some-user-id",
    )

    # Test with None
    msg_type3, meta3 = _crew_map_response("question_card", {}, None)
    check("None sender_id stays None", meta3["target_user_id"] is None)


# -----------------------------------------------------------------------
# 9. Smart Option Extraction
# -----------------------------------------------------------------------
def test_smart_option_extraction():
    section("9. Smart Option Extraction")
    from app.services.crew_agent_service import CrewAgentService

    # "X or Y" pattern
    opts = CrewAgentService._try_extract_options("indian dinner or italian")
    check("'indian dinner or italian' -> 2 options", len(opts) == 2, f"got {opts}")
    check("first option capitalized", opts[0] == "Indian dinner" if opts else False, f"got {opts}")
    check("second option capitalized", opts[1] == "Italian" if len(opts) > 1 else False, f"got {opts}")

    # "question about X or Y" — strips filler
    opts2 = CrewAgentService._try_extract_options("question about hiking or beach")
    check("'question about X or Y' -> 2 options", len(opts2) == 2, f"got {opts2}")

    # "A, B, or C"
    opts3 = CrewAgentService._try_extract_options("pizza, pasta, or sushi")
    check("'pizza, pasta, or sushi' -> 3 options", len(opts3) == 3, f"got {opts3}")

    # Comma-separated without "or"
    opts4 = CrewAgentService._try_extract_options("red, blue, green")
    check("'red, blue, green' -> 3 options", len(opts4) == 3, f"got {opts4}")

    # No options extractable (single item)
    opts5 = CrewAgentService._try_extract_options("what time to meet")
    check("'what time to meet' -> no options", len(opts5) == 0, f"got {opts5}")

    # "the X or the Y" — strips "the"
    opts6 = CrewAgentService._try_extract_options("the indian dinner or the italian one")
    check("strips 'the' prefix", len(opts6) == 2, f"got {opts6}")


# -----------------------------------------------------------------------
# 10. Full E2E — Tier 1 direct execution (all fields present)
# -----------------------------------------------------------------------
def test_direct_execution():
    section("10. Direct Execution (Tier 1 — all fields)")
    from app.infrastructure.cache.redis import redis_client
    from app.infrastructure.db.connection import get_db
    from app.services.crew_agent_service import CrewAgentService

    redis = redis_client if redis_client and redis_client.available else None

    # Full poll command with all fields — should skip Q&A
    with get_db() as session:
        success, result = CrewAgentService.process(
            session=session,
            group_id="test-group-crew-direct",
            sender_id="test-sender-crew-direct",
            message_content="@crew create poll: What to eat? Options: Pizza, Pasta",
            redis_client=redis,
        )

    # With a fake group_id, the PollService call will likely fail,
    # so we expect either success_text or error_text (not a question_card)
    response_type = result.get("response_type", "")
    check(
        "full command -> not a question_card (no Q&A needed)",
        response_type != "question_card",
        f"got {response_type}",
    )
    check(
        "full command -> either success or error (not stuck)",
        response_type in ("success_text", "error_text"),
        f"got {response_type}",
    )
    print(f"  INFO  result: {result.get('content', '')[:100]}")


# -----------------------------------------------------------------------
# 11. Schedule intent classification
# -----------------------------------------------------------------------
def test_schedule_classification():
    section("11. Schedule Intent Classification")
    from app.services.crew_parsers import INTENT_SCHEDULE_PLACE, CrewParsers

    cases = [
        ("@crew schedule kerry park to april 2nd 10am", INTENT_SCHEDULE_PLACE, 1.0,
         {"place_name": "kerry park", "datetime_raw": "april 2nd 10am"}),
        ("@crew move gas works park to tomorrow 3pm", INTENT_SCHEDULE_PLACE, 1.0,
         {"place_name": "gas works park", "datetime_raw": "tomorrow 3pm"}),
        ("@crew reschedule pike place market to dec 15", INTENT_SCHEDULE_PLACE, 1.0,
         {"place_name": "pike place market", "datetime_raw": "dec 15"}),
        ("@crew schedule kerry park", INTENT_SCHEDULE_PLACE, 0.7, {"place_name": "kerry park"}),
    ]

    for text, expected_intent, expected_conf, expected_entities in cases:
        intent, entities, conf = CrewParsers.classify(text)
        label = text[:55]
        check(f"intent: {label}", intent == expected_intent, f"got {intent}")
        check(f"confidence: {label}", conf == expected_conf, f"got {conf}")
        for key, val in expected_entities.items():
            check(f"entity[{key}]: {label}", entities.get(key) == val,
                  f"got {entities.get(key)}")


# -----------------------------------------------------------------------
# 12. Reverse delete regex and fuzzy search patterns
# -----------------------------------------------------------------------
def test_reverse_delete_and_fuzzy():
    section("12. Reverse Delete & Fuzzy Patterns")
    from app.services.crew_parsers import INTENT_DELETE_ITEM, CrewParsers

    # Reverse delete: entity_type at end
    cases = [
        ("@crew delete the kerry park place", INTENT_DELETE_ITEM, 1.0,
         {"entity_type": "place", "search_text": "kerry park"}),
        ("@crew remove the dinner poll", INTENT_DELETE_ITEM, 1.0,
         {"entity_type": "poll", "search_text": "dinner"}),
        ("@crew delete the pack bags checklist", INTENT_DELETE_ITEM, 1.0,
         {"entity_type": "checklist", "search_text": "pack bags"}),
    ]

    for text, expected_intent, expected_conf, expected_entities in cases:
        intent, entities, conf = CrewParsers.classify(text)
        label = text[:55]
        check(f"intent: {label}", intent == expected_intent, f"got {intent}")
        check(f"confidence: {label}", conf == expected_conf, f"got {conf}")
        for key, val in expected_entities.items():
            check(f"entity[{key}]: {label}", entities.get(key) == val,
                  f"got {entities.get(key)}")


# -----------------------------------------------------------------------
# 13. Bulk field parsing
# -----------------------------------------------------------------------
def test_bulk_fields():
    section("13. Bulk Field Parsing")
    from app.services.crew_agent_service import CrewAgentService

    # Valid bulk submission
    msg = '__crew_fields__:{"question": "Where to eat", "options": ["Pizza", "Pasta"]}'
    result = CrewAgentService._try_parse_bulk_fields(msg)
    check("bulk parse -> not None", result is not None)
    check("bulk parse -> question present", result.get("question") == "Where to eat")
    check("bulk parse -> options list", result.get("options") == ["Pizza", "Pasta"])

    # Non-bulk message
    result2 = CrewAgentService._try_parse_bulk_fields("just a regular message")
    check("non-bulk -> None", result2 is None)

    # Invalid JSON
    result3 = CrewAgentService._try_parse_bulk_fields("__crew_fields__:{bad json}")
    check("invalid json -> None", result3 is None)


# -----------------------------------------------------------------------
# 14. Natural language date parsing
# -----------------------------------------------------------------------
def test_datetime_parsing():
    section("14. Natural Language Date Parsing")
    from datetime import date, timedelta

    from app.services.crew_agent_service import CrewAgentService

    # Tomorrow
    d, t = CrewAgentService._parse_datetime_natural("tomorrow 3pm")
    expected_date = (date.today() + timedelta(days=1)).isoformat()
    check("tomorrow -> correct date", d == expected_date, f"got {d}")
    check("3pm -> 15:00", t == "15:00", f"got {t}")

    # Today
    d, t = CrewAgentService._parse_datetime_natural("today 10am")
    check("today -> correct date", d == date.today().isoformat(), f"got {d}")
    check("10am -> 10:00", t == "10:00", f"got {t}")

    # 24h format
    d, t = CrewAgentService._parse_datetime_natural("tomorrow 14:30")
    check("14:30 -> 14:30", t == "14:30", f"got {t}")

    # Garbage
    d, t = CrewAgentService._parse_datetime_natural("asdfgh")
    check("garbage -> None date", d is None, f"got {d}")


def test_llm_extraction_parsing():
    section("15. LLM Extraction Parses schedule_place + datetime_raw")
    from app.services.crew_parsers import INTENT_SCHEDULE_PLACE, CrewParsers

    # Simulated LLM response for "add timing and date in the kerry park"
    raw_json = json.dumps({
        "intent": "schedule_place",
        "place_name": "Kerry Park",
        "datetime_raw": "april 2nd 10am",
        "question": None,
        "options": None,
    })
    intent, entities = CrewParsers.parse_llm_extraction(raw_json)
    check("schedule_place accepted", intent == INTENT_SCHEDULE_PLACE, f"got {intent}")
    check("place_name extracted", entities.get('place_name') == 'Kerry Park', f"{entities}")
    check("datetime_raw extracted", entities.get('datetime_raw') == 'april 2nd 10am', f"{entities}")

    # Verify prompt includes schedule_place
    prompt = CrewParsers.build_extraction_prompt("add timing to park")
    check("prompt has schedule_place", 'schedule_place' in prompt, "missing from prompt")
    check("prompt has datetime_raw", 'datetime_raw' in prompt, "missing from prompt")


# -----------------------------------------------------------------------
# Run all
# -----------------------------------------------------------------------
if __name__ == "__main__":
    start = time.time()
    print("\n" + "=" * 60)
    print("  @crew Agent Test Suite")
    print("=" * 60)

    test_config()
    test_tier1_classification()
    test_tier2_classification()
    test_unknown_classification()
    test_conversation_state()
    test_agent_process()
    test_cancel_flow()
    test_uuid_serialization()
    test_smart_option_extraction()
    test_direct_execution()
    test_schedule_classification()
    test_reverse_delete_and_fuzzy()
    test_bulk_fields()
    test_datetime_parsing()
    test_llm_extraction_parsing()

    elapsed = round(time.time() - start, 2)
    print(f"\n{'=' * 60}")
    print(f"  Results: {_passed} passed, {_failed} failed ({elapsed}s)")
    print(f"{'=' * 60}")

    if _errors:
        print("\nFailures:")
        for name, detail in _errors:
            print(f"  - {name}: {detail}")

    sys.exit(1 if _failed else 0)
