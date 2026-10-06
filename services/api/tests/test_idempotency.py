# Purpose: Regression tests for idempotency, including success and failure behavior.
"""Step 3 — idempotency scoping, reservation and caching policy.

Backed by an in-memory Redis stand-in so the behaviour is asserted exactly,
including the concurrency case, without needing a live server.
"""
import json
import time

import pytest
from conftest import ApiClient
from app.core.idempotency import _MUTATING_METHODS


class FakeRedis:
    """Just enough Redis: get / set(nx, ex) / delete, with expiry."""

    def __init__(self):
        self.store = {}  # key -> (value, expires_at or None)
        self.set_calls = []

    def _live(self, key):
        entry = self.store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and expires_at <= time.time():
            del self.store[key]
            return None
        return value

    def get(self, key):
        return self._live(key)

    def set(self, key, value, nx=False, ex=None):
        self.set_calls.append((key, nx, ex))
        if nx and self._live(key) is not None:
            return None
        self.store[key] = (value, time.time() + ex if ex else None)
        return True

    def delete(self, key):
        self.store.pop(key, None)
        return 1


@pytest.fixture
def fake_redis(app):
    previous = app.extensions.get("redis")
    fake = FakeRedis()
    app.extensions["redis"] = fake
    yield fake
    app.extensions["redis"] = previous


KEY = "idem-key-aaaaaaaaaaaa"


def _create_group(api, key=None, name="Idem group"):
    headers = {"Idempotency-Key": key} if key else None
    return api.post("/api/v1/expenses/groups", json={"name": name}, headers=headers)


# ---------------------------------------------------------------------------
# P0-13 — cross-user replay
# ---------------------------------------------------------------------------

def test_key_is_scoped_to_the_caller(fake_redis, make_user):
    """The same Idempotency-Key from two users must not collide.

    Previously the key was the bare header value, so user B received user A's
    stored response and B's own request never executed.
    """
    alice_api, _, _ = make_user("alice")
    bob_api, _, _ = make_user("bob")

    first = _create_group(alice_api, KEY, name="Alice group")
    assert first.status_code in (200, 201), first.get_json()

    second = _create_group(bob_api, KEY, name="Bob group")
    assert second.status_code in (200, 201), second.get_json()
    assert "X-Idempotent-Replay" not in second.headers

    alice_name = (first.get_json()["data"]["group"])["name"]
    bob_name = (second.get_json()["data"]["group"])["name"]
    assert alice_name == "Alice group"
    assert bob_name == "Bob group"


def test_key_is_scoped_to_method_and_path(fake_redis, alice):
    """The same key on a different route must not replay the first result."""
    api, _, _ = alice
    created = _create_group(api, KEY)
    assert created.status_code in (200, 201)

    other = api.post(
        "/api/v1/expenses",
        json={"description": "Solo lunch", "amount": 12.0},
        headers={"Idempotency-Key": KEY},
    )
    assert "X-Idempotent-Replay" not in other.headers
    assert other.status_code in (200, 201), other.get_json()


# ---------------------------------------------------------------------------
# Replay of a genuine retry
# ---------------------------------------------------------------------------

def test_same_caller_same_key_replays(fake_redis, alice):
    api, _, _ = alice
    first = _create_group(api, KEY, name="Only once")
    assert first.status_code in (200, 201)
    assert "X-Idempotent-Replay" not in first.headers

    second = _create_group(api, KEY, name="Only once")
    assert second.headers.get("X-Idempotent-Replay") == "true"
    assert second.get_data(as_text=True) == first.get_data(as_text=True)


# ---------------------------------------------------------------------------
# P1-15 — atomic reservation, and what gets cached
# ---------------------------------------------------------------------------

def test_reservation_is_atomic(fake_redis, alice):
    """The claim must use SET NX, not a read-then-write."""
    api, _, _ = alice
    _create_group(api, KEY)
    nx_calls = [c for c in fake_redis.set_calls if c[1] is True]
    assert nx_calls, "no SET NX issued; the key was not atomically reserved"


def test_concurrent_duplicate_is_rejected_not_executed(fake_redis, alice):
    """A second request arriving while the first is still in flight gets 409.

    Simulated by leaving the reservation marker in place, which is exactly
    the state Redis holds mid-request.
    """
    api, _, _ = alice
    # Reserve as the middleware would, then send the duplicate.
    sent = _create_group(api, KEY)
    assert sent.status_code in (200, 201)

    # Reset the stored result back to the in-flight marker.
    key = next(iter(fake_redis.store))
    fake_redis.store[key] = ("__in_flight__", None)

    duplicate = _create_group(api, KEY)
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "IDEMPOTENT_REQUEST_IN_PROGRESS"


def test_error_responses_are_not_cached(fake_redis, alice):
    """A 4xx must not be replayed for 24 hours."""
    api, _, _ = alice
    bad = api.post(
        "/api/v1/expenses/groups",
        json={},  # missing name -> validation error
        headers={"Idempotency-Key": KEY},
    )
    assert bad.status_code >= 400
    assert fake_redis.store == {}, "a failed response was cached"

    # The same key is now free, so a corrected retry executes for real.
    good = _create_group(api, KEY, name="Now valid")
    assert good.status_code in (200, 201), good.get_json()
    assert "X-Idempotent-Replay" not in good.headers


def test_patch_is_covered(fake_redis, alice):
    """PATCH mutates and was not covered by the middleware at all."""
    api, _, _ = alice
    api.patch(
        "/api/v1/users/me",
        json={"display_name": "Patched"},
        headers={"Idempotency-Key": KEY},
    )
    assert fake_redis.set_calls, "PATCH never reached the idempotency hook"


def test_delete_is_covered():
    """DELETE is a state-changing request and must reserve its key too."""
    assert 'DELETE' in _MUTATING_METHODS


# ---------------------------------------------------------------------------
# P2-27 — key validation and bounded storage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_key", ["short", "x" * 201, "has space", "semi;colon"])
def test_malformed_keys_are_rejected(fake_redis, alice, bad_key):
    api, _, _ = alice
    response = _create_group(api, bad_key)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_IDEMPOTENCY_KEY"


def test_stored_key_is_a_bounded_digest(fake_redis, alice):
    api, _, _ = alice
    _create_group(api, "a" * 200)
    stored_key = next(iter(fake_redis.store))
    # "idempotency:" + 64 hex characters, regardless of input length.
    assert stored_key.startswith("idempotency:")
    assert len(stored_key) == len("idempotency:") + 64


def test_no_key_header_means_no_redis_traffic(fake_redis, alice):
    api, _, _ = alice
    _create_group(api)
    assert fake_redis.set_calls == []
