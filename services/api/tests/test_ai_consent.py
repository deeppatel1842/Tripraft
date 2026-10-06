# Purpose: Regression tests for ai consent, including success and failure behavior.
"""Step 4 — the AI agents' consent promises must be real.

The audit's sharpest finding was that "@scout forget me" did nothing while
telling the user it had worked. These tests hold the whole erasure path.
"""
import uuid

import pytest
from conftest import payload

from app.scout.models import AIAgentLog, AIConsent, AIPreferenceProfile
from app.trips.models import ChatMessage, ChatSummary
from app.core.db.connection import get_db_session
from app.core.cache.redis import RedisClient
from app.scout.llm.ollama_client import OllamaClient
from app.scout.services.consent_gate import ConsentGate
from app.scout.services.crew_agent_service import CrewAgentService, _missing_fields
from app.scout.services.scout_agent_service import ScoutAgentService


@pytest.fixture
def travel_group(alice):
    api, user_id, email = alice
    response = api.post(
        "/api/v1/group-planner/groups",
        json={"name": "Consent %s" % uuid.uuid4().hex[:6], "destination": "Kyoto"},
    )
    assert response.status_code in (200, 201), response.get_json()
    body = payload(response)
    group_id = (body.get("group") or body)["id"]
    return api, user_id, group_id


def _seed_ai_data(group_id, user_id):
    """Write the three kinds of record a revocation is supposed to erase."""
    with get_db_session() as session:
        session.add(AIPreferenceProfile(
            group_id=uuid.UUID(str(group_id)),
            user_id=uuid.UUID(str(user_id)),
            preference_key="home_country",
            preference_value="India",
            source="explicit",
        ))
        session.add(AIAgentLog(
            group_id=uuid.UUID(str(group_id)),
            user_id=uuid.UUID(str(user_id)),
            agent="scout",
            intent="complex",
            query_text="what should i pack",
            response_summary="a summary that quotes the user",
            tokens_used=10,
            latency_ms=5,
        ))
        messages = [ChatMessage(
            group_id=uuid.UUID(str(group_id)),
            sender_id=uuid.UUID(str(user_id)),
            content=content,
        ) for content in ('First preference', 'Second preference')]
        session.add_all(messages)
        session.flush()
        session.add(ChatSummary(
            group_id=uuid.UUID(str(group_id)),
            from_message_id=messages[0].id,
            to_message_id=messages[1].id,
            summary_text="Alice prefers vegetarian food",
        ))
        session.commit()


def _counts(group_id, user_id):
    with get_db_session() as session:
        return {
            "preferences": session.query(AIPreferenceProfile).filter_by(
                group_id=uuid.UUID(str(group_id)),
                user_id=uuid.UUID(str(user_id)),
            ).count(),
            "logs": session.query(AIAgentLog).filter_by(
                group_id=uuid.UUID(str(group_id)),
                user_id=uuid.UUID(str(user_id)),
            ).count(),
            "summaries": session.query(ChatSummary).filter_by(
                group_id=uuid.UUID(str(group_id)),
            ).count(),
        }


# ---------------------------------------------------------------------------
# P1-35 — revoke must erase everything it claims to
# ---------------------------------------------------------------------------

def test_revoke_deletes_preferences_logs_and_summaries(travel_group):
    _, user_id, group_id = travel_group
    _seed_ai_data(group_id, user_id)
    assert _counts(group_id, user_id) == {
        "preferences": 1, "logs": 1, "summaries": 1
    }

    with get_db_session() as session:
        assert ConsentGate.revoke(session, group_id, user_id) is True
        session.commit()

    assert _counts(group_id, user_id) == {
        "preferences": 0, "logs": 0, "summaries": 0
    }


def test_revoke_is_idempotent_without_a_consent_row(travel_group):
    """It returned False when no AIConsent row existed, which made erasure
    unreachable for the users who most needed it: a user who never saw a
    consent card could still have preference rows written about them."""
    _, user_id, group_id = travel_group
    _seed_ai_data(group_id, user_id)

    with get_db_session() as session:
        assert session.query(AIConsent).filter_by(
            group_id=uuid.UUID(str(group_id)),
            user_id=uuid.UUID(str(user_id)),
        ).count() == 0
        assert ConsentGate.revoke(session, group_id, user_id) is True
        session.commit()

    assert _counts(group_id, user_id)["preferences"] == 0


def test_revoke_can_be_called_twice(travel_group):
    _, user_id, group_id = travel_group
    with get_db_session() as session:
        assert ConsentGate.revoke(session, group_id, user_id) is True
        assert ConsentGate.revoke(session, group_id, user_id) is True
        session.commit()


def test_delete_consent_endpoint_does_not_404(travel_group):
    """The REST "forget me" answered 404 for a user with no consent row."""
    api, user_id, group_id = travel_group
    _seed_ai_data(group_id, user_id)

    response = api.delete("/api/v1/group-planner/groups/%s/ai/consent" % group_id)
    assert response.status_code == 200, response.get_json()
    assert payload(response)["revoked"] is True
    assert _counts(group_id, user_id)["preferences"] == 0


def test_delete_consent_message_does_not_overclaim(travel_group):
    """The old copy promised "summaries updated" while touching none."""
    api, user_id, group_id = travel_group
    response = api.delete("/api/v1/group-planner/groups/%s/ai/consent" % group_id)
    message = payload(response)["message"]
    assert "summaries updated" not in message.lower()


# ---------------------------------------------------------------------------
# P0-9 — the chat command must act, not echo
# ---------------------------------------------------------------------------

def test_opt_out_in_chat_revokes_and_does_not_echo_the_marker(travel_group):
    """process() returns {'response': 'consent_opt_out'} and the live chat
    path had no branch for it, so it posted that literal string into the
    group and changed nothing."""
    api, user_id, group_id = travel_group

    with get_db_session() as session:
        ConsentGate.grant(
            session=session, group_id=group_id, user_id=user_id,
            jurisdiction="GDPR", ip_address="127.0.0.1",
        )
        session.commit()
    _seed_ai_data(group_id, user_id)

    sent = api.post(
        "/api/v1/group-planner/groups/%s/messages" % group_id,
        json={"content": "@scout forget me", "type": "text"},
    )
    assert sent.status_code in (200, 201), sent.get_json()

    listed = api.get("/api/v1/group-planner/groups/%s/messages" % group_id)
    contents = [
        m.get("content", "")
        for m in (payload(listed).get("messages") or [])
    ]
    assert not any("consent_opt_out" in c for c in contents), (
        "the raw consent marker was posted into chat: %s" % contents
    )

    # And the data is actually gone.
    assert _counts(group_id, user_id)["preferences"] == 0
    with get_db_session() as session:
        row = session.query(AIConsent).filter_by(
            group_id=uuid.UUID(str(group_id)),
            user_id=uuid.UUID(str(user_id)),
        ).first()
        assert row is not None and row.granted is False
        assert row.revoked_at is not None


def test_opt_in_in_chat_grants_consent(travel_group):
    api, user_id, group_id = travel_group
    sent = api.post(
        "/api/v1/group-planner/groups/%s/messages" % group_id,
        json={"content": "@scout opt in", "type": "text"},
    )
    assert sent.status_code in (200, 201), sent.get_json()

    with get_db_session() as session:
        row = session.query(AIConsent).filter_by(
            group_id=uuid.UUID(str(group_id)),
            user_id=uuid.UUID(str(user_id)),
        ).first()
    assert row is not None and row.granted is True


# ---------------------------------------------------------------------------
# P0-10 / P1-34 — the "consent-free" set must really touch no user data
# ---------------------------------------------------------------------------

def test_preference_update_is_not_consent_free():
    """It upserts AIPreferenceProfile rows, so it is a data write."""
    import inspect

    source = inspect.getsource(ScoutAgentService.process)
    consent_free = source.split("_CONSENT_FREE = {", 1)[1].split("}", 1)[0]
    assert "'preference_update'" not in consent_free


def test_scout_does_not_log_a_nonconsenting_user(travel_group):
    """P0-10: even a consent-free answer must not persist query/response text."""
    _, user_id, group_id = travel_group
    scout = ScoutAgentService()

    with get_db_session() as session:
        scout._log_interaction(
            session, group_id, user_id, "weather", "weather in Kyoto?",
            "Sunny and mild.", 0, 1,
        )
        session.commit()

    assert _counts(group_id, user_id)["logs"] == 0


def test_scout_logs_only_after_consent(travel_group):
    """The privacy gate should not disable audit logging for an opt-in user."""
    _, user_id, group_id = travel_group
    scout = ScoutAgentService()

    with get_db_session() as session:
        ConsentGate.grant(
            session=session, group_id=group_id, user_id=user_id,
            jurisdiction="GDPR", ip_address="127.0.0.1",
        )
        scout._log_interaction(
            session, group_id, user_id, "weather", "weather in Kyoto?",
            "Sunny and mild.", 0, 1,
        )
        session.commit()

    assert _counts(group_id, user_id)["logs"] == 1


def test_user_origin_is_not_read_without_consent(travel_group):
    """visa / flight_range stay consent-free, so the personal-data read they
    depend on has to be gated instead."""
    _, user_id, group_id = travel_group
    _seed_ai_data(group_id, user_id)

    scout = ScoutAgentService()
    with get_db_session() as session:
        assert scout._get_user_origin(session, group_id, user_id) is None


def test_user_origin_is_read_once_consented(travel_group):
    _, user_id, group_id = travel_group
    _seed_ai_data(group_id, user_id)

    scout = ScoutAgentService()
    with get_db_session() as session:
        ConsentGate.grant(
            session=session, group_id=group_id, user_id=user_id,
            jurisdiction="GDPR", ip_address="127.0.0.1",
        )
        session.commit()
        assert scout._get_user_origin(session, group_id, user_id) == "India"


# ---------------------------------------------------------------------------
# P1-37 â€” non-equal Crew expenses must collect and pass split values
# ---------------------------------------------------------------------------

def test_crew_non_equal_expense_requires_parseable_splits():
    first, second = str(uuid.uuid4()), str(uuid.uuid4())
    entities = {
        "amount": 100,
        "description": "Dinner",
        "split_type": "percentage",
    }

    assert _missing_fields("create_expense", entities) == ["splits"]
    splits = CrewAgentService._parse_field_answer(
        "splits", "%s=60, %s=40" % (first, second), "percentage",
    )
    assert splits == [
        {"user_id": first, "percentage": 60.0},
        {"user_id": second, "percentage": 40.0},
    ]
    entities["splits"] = splits
    assert _missing_fields("create_expense", entities) == []


# ---------------------------------------------------------------------------
# P1-33 / P1-38 — consent-scoped cache and one-time confirmations
# ---------------------------------------------------------------------------

def test_semantic_cache_key_is_scoped_to_sender_and_consent_context():
    first = OllamaClient.cache_key('group', 'best hotels', 'sender-a', ['user-1', 'user-2'])
    same_context_different_order = OllamaClient.cache_key(
        'group', 'best hotels', 'sender-a', ['user-2', 'user-1'],
    )
    different_sender = OllamaClient.cache_key('group', 'best hotels', 'sender-b', ['user-1', 'user-2'])
    different_consent = OllamaClient.cache_key('group', 'best hotels', 'sender-a', ['user-1'])

    assert first == same_context_different_order
    assert first != different_sender
    assert first != different_consent


def test_crew_does_not_offer_confirmation_without_redis_state(monkeypatch):
    monkeypatch.setattr(
        CrewAgentService, '_fuzzy_search_entity',
        staticmethod(lambda *args: [{'id': uuid.uuid4(), 'name': 'Private place'}]),
    )

    ok, result = CrewAgentService._handle_delete_item(
        None, 'group', 'user',
        {'entity_type': 'place', 'search_text': 'private place'},
        None,
    )
    assert not ok
    assert 'temporarily unavailable' in result['content'].lower()


def test_redis_getdel_consumes_a_value_atomically():
    class FakeClient:
        def __init__(self):
            self.values = {'once': 'pending'}

        def getdel(self, key):
            return self.values.pop(key, None)

    redis = RedisClient()
    redis._available = True
    redis._client = FakeClient()
    assert redis.getdel('once') == 'pending'
    assert redis.getdel('once') is None


def test_confirmation_route_uses_atomic_getdel():
    import inspect
    from app.scout.routes import ai_confirm

    assert 'getdel(pending_key)' in inspect.getsource(ai_confirm.confirm_crew_action)
