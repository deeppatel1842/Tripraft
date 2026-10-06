# Purpose: Regression tests for group planner smoke, including success and failure behavior.
"""Smoke coverage for the group-planner surfaces whose schemas hold ids.

These exist so the integer -> UUID schema conversion cannot quietly break
chat, checklists or polls. They assert the flows still work end to end, not
that the underlying behaviour is correct.
"""
import uuid

import pytest
from conftest import payload


@pytest.fixture
def travel_group(alice):
    api, user_id, _ = alice
    response = api.post(
        "/api/v1/group-planner/groups",
        json={
            "name": "Planner %s" % uuid.uuid4().hex[:6],
            "destination": "Lisbon",
        },
    )
    assert response.status_code in (200, 201), response.get_json()
    group = payload(response).get("group") or payload(response)
    group_id = group.get("id")
    assert group_id, response.get_json()
    return api, user_id, group_id


# ---------------------------------------------------------------------------
# Chat — SendMessageSchema.parent_message_id and ReadReceiptSchema
# ---------------------------------------------------------------------------

def test_chat_send_and_list(travel_group):
    api, _, group_id = travel_group
    sent = api.post(
        "/api/v1/group-planner/groups/%s/messages" % group_id,
        json={"content": "hello crew", "type": "text"},
    )
    assert sent.status_code in (200, 201), sent.get_json()

    listed = api.get("/api/v1/group-planner/groups/%s/messages" % group_id)
    assert listed.status_code == 200, listed.get_json()


def test_chat_threaded_reply_accepts_uuid_parent(travel_group):
    """parent_message_id was fields.Integer with a min=1 range check, so a
    real UUID message id could never be referenced."""
    api, _, group_id = travel_group
    first = api.post(
        "/api/v1/group-planner/groups/%s/messages" % group_id,
        json={"content": "parent message", "type": "text"},
    )
    message = payload(first).get("message") or payload(first)
    parent_id = message.get("id")
    assert parent_id, first.get_json()

    reply = api.post(
        "/api/v1/group-planner/groups/%s/messages" % group_id,
        json={"content": "child message", "type": "text",
              "parent_message_id": parent_id},
    )
    assert reply.status_code in (200, 201), reply.get_json()


def test_chat_read_receipt_accepts_uuid_message_id(travel_group):
    """ReadReceiptSchema.last_read_message_id was an integer field (declared
    four times over)."""
    api, _, group_id = travel_group
    sent = api.post(
        "/api/v1/group-planner/groups/%s/messages" % group_id,
        json={"content": "mark me read", "type": "text"},
    )
    message = payload(sent).get("message") or payload(sent)
    message_id = message.get("id")
    assert message_id, sent.get_json()

    response = api.post(
        "/api/v1/group-planner/groups/%s/messages/read" % group_id,
        json={"last_read_message_id": message_id},
    )
    assert response.status_code in (200, 201, 204), response.get_json()


def test_chat_read_receipt_rejects_integer_message_id(travel_group):
    api, _, group_id = travel_group
    response = api.post(
        "/api/v1/group-planner/groups/%s/messages/read" % group_id,
        json={"last_read_message_id": 1},
    )
    assert response.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Checklist — assigned_to_id
# ---------------------------------------------------------------------------

def test_checklist_create_and_toggle(travel_group):
    api, _, group_id = travel_group
    created = api.post(
        "/api/v1/group-planner/groups/%s/checklist" % group_id,
        json={"text": "Book flights"},
    )
    assert created.status_code in (200, 201), created.get_json()
    # The serializer returns the item itself as `data`; its "item" key holds
    # the text, not a nested object.
    item_id = payload(created).get("id")
    assert item_id, created.get_json()

    toggled = api.post(
        "/api/v1/group-planner/checklist/%s/toggle" % item_id, json={}
    )
    assert toggled.status_code in (200, 201), toggled.get_json()


def test_checklist_accepts_uuid_assignee(travel_group):
    """assigned_to_id was fields.Integer while users have UUID ids."""
    api, user_id, group_id = travel_group
    response = api.post(
        "/api/v1/group-planner/groups/%s/checklist" % group_id,
        json={"text": "Pack bags", "assigned_to_id": user_id},
    )
    assert response.status_code in (200, 201), response.get_json()


def test_checklist_rejects_integer_assignee(travel_group):
    api, _, group_id = travel_group
    response = api.post(
        "/api/v1/group-planner/groups/%s/checklist" % group_id,
        json={"text": "Bad assignee", "assigned_to_id": 3},
    )
    assert response.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Polls — option_index stays an integer on purpose
# ---------------------------------------------------------------------------

def test_poll_create_and_vote(travel_group):
    api, _, group_id = travel_group
    created = api.post(
        "/api/v1/group-planner/groups/%s/polls" % group_id,
        json={"question": "Where to eat?", "options": ["Tapas", "Sushi"]},
    )
    assert created.status_code in (200, 201), created.get_json()
    poll = payload(created).get("poll") or payload(created)
    poll_id = poll.get("id")
    assert poll_id, created.get_json()

    voted = api.post(
        "/api/v1/group-planner/groups/%s/polls/%s/vote" % (group_id, poll_id),
        json={"option_index": 0},
    )
    assert voted.status_code in (200, 201), voted.get_json()
