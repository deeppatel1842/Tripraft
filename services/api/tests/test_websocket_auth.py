# Purpose: Regression tests for websocket auth, including success and failure behavior.
"""Step 3 — the chat socket must accept UUID subjects.

`handle_connect` read the subject as
`payload.get("user_id", int(payload.get("sub", 0)))`. Python evaluates a
default argument eagerly, so `int()` ran against a UUIDv7 string on every
connection -- even when `user_id` was present -- and the handler raised
before any user could join (audit P0-15). Presence then dropped every member
for the same reason (audit P2-20).
"""
import uuid

import pytest

from app.auth.security.jwt import create_access_token
from app.trips.realtime.socketio_ext import socketio


@pytest.fixture
def token(alice):
    _, user_id, email = alice
    return create_access_token(user_id=user_id, email=email, display_name="Alice"), user_id


def test_connect_accepts_a_uuid_subject(app, token):
    access_token, user_id = token
    client = socketio.test_client(app, auth={"token": access_token})
    try:
        assert client.is_connected(), "socket refused a valid UUID-subject token"
    finally:
        client.disconnect()


def test_joining_a_group_room_resolves_the_stored_uuid(app, alice):
    """Proves the stored subject is a usable UUID, not NaN or a 0 fallback.

    join_group only reaches its presence broadcast after looking the user up
    as an active TripMember with the id held on the socket session.
    """
    api, user_id, email = alice
    created = api.post(
        "/api/v1/group-planner/groups",
        json={"name": "Socket group %s" % uuid.uuid4().hex[:6], "destination": "Porto"},
    )
    assert created.status_code in (200, 201), created.get_json()
    body = created.get_json()["data"]
    group_id = (body.get("group") or body)["id"]

    access_token = create_access_token(
        user_id=user_id, email=email, display_name="Alice"
    )
    client = socketio.test_client(app, auth={"token": access_token})
    try:
        assert client.is_connected()
        client.get_received()  # drain anything from connect
        client.emit("join_group", {"group_id": group_id})
        events = [e["name"] for e in client.get_received()]
        assert "presence:update" in events, (
            "join_group never got past the membership lookup; received %s" % events
        )
    finally:
        client.disconnect()


def test_connect_without_a_token_is_refused(app):
    client = socketio.test_client(app, auth={})
    assert not client.is_connected()


def test_connect_with_a_garbage_token_is_refused(app):
    client = socketio.test_client(app, auth={"token": "not-a-jwt"})
    assert not client.is_connected()


def test_presence_list_keeps_uuid_ids(app):
    """int(uid_str) raised on every entry and the except skipped it, so the
    online list was always empty."""
    from app.trips.realtime import events

    group_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    class FakeRedis:
        def hgetall(self, key):
            import json
            return {user_id: json.dumps({"email": "a@b.test", "joined_at": "now"})}

    original = events._get_redis
    events._get_redis = lambda: FakeRedis()
    try:
        online = events._get_presence_list(group_id)
    finally:
        events._get_redis = original

    assert len(online) == 1, "presence dropped the member"
    assert online[0]["user_id"] == user_id
