# Purpose: Test fixture/configuration helper for conftest.
"""Shared pytest fixtures for the TripRaft backend test suite.

The database URL is set before any application module is imported, so a test
run can never touch the developer's real SQLite file.
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Must happen before `app.*` is imported: Config reads DATABASE_URL at class
# definition time.
_TEST_DB = Path(tempfile.gettempdir()) / ("tripraft-test-%s.db" % uuid.uuid4().hex[:12])
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.as_posix()
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-0123456789")
os.environ.setdefault("FLASK_ENV", "development")

# No Redis in the test environment. Empty rather than unset so SocketIO does
# not attach a message queue -- flask-socketio's test client refuses to run
# against one, and cross-process fan-out is not something an in-process test
# could exercise anyway. Tests that need Redis install a fake in
# app.extensions["redis"].
os.environ["REDIS_URL"] = ""


@pytest.fixture(scope="session")
def app():
    """The Flask application, built once against a throwaway database."""
    from app.core.factory import create_app
    from alembic import command
    from alembic.config import Config as AlembicConfig

    # Exercise the same schema entry point as a real installation. Tests must
    # never hide missing migrations behind metadata.create_all().
    config = AlembicConfig(str(BACKEND_ROOT / 'alembic.ini'))
    config.set_main_option('script_location', str(BACKEND_ROOT / 'migrations'))
    command.upgrade(config, 'head')

    application = create_app()
    application.config["TESTING"] = True
    yield application

    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(_TEST_DB) + suffix)
        try:
            candidate.unlink()
        except OSError:
            pass


class ApiClient:
    """Test client that speaks the app's double-submit CSRF contract.

    Mutating requests need the `csrf_token` cookie echoed back in the
    `X-CSRF-Token` header; a plain test client omits it and every POST
    would 403.
    """

    def __init__(self, application):
        self._client = application.test_client()

    @property
    def raw(self):
        return self._client

    def _headers(self, supplied):
        headers = dict(supplied or {})
        cookie = self._client.get_cookie("csrf_token")
        if cookie is not None:
            headers.setdefault(
                "X-CSRF-Token", getattr(cookie, "value", cookie)
            )
        return headers

    def _call(self, verb, path, headers=None, **kwargs):
        return getattr(self._client, verb)(
            path, headers=self._headers(headers), **kwargs
        )

    def get(self, path, **kw):
        return self._call("get", path, **kw)

    def post(self, path, **kw):
        return self._call("post", path, **kw)

    def put(self, path, **kw):
        return self._call("put", path, **kw)

    def patch(self, path, **kw):
        return self._call("patch", path, **kw)

    def delete(self, path, **kw):
        return self._call("delete", path, **kw)


def payload(response):
    """The `data` envelope of a response, or {} when there is none."""
    body = response.get_json(silent=True) or {}
    return body.get("data") or {}


def error_of(response):
    """The `error` envelope of a response, or {}."""
    body = response.get_json(silent=True) or {}
    return body.get("error") or {}


@pytest.fixture
def client(app):
    """A fresh, unauthenticated API client."""
    return ApiClient(app)


@pytest.fixture
def make_user(app):
    """Factory: signs up a new user and returns (client, user_id, email)."""

    def _make(label="user"):
        api = ApiClient(app)
        email = "%s_%s@example.test" % (label, uuid.uuid4().hex[:10])
        response = api.post(
            "/api/v1/auth/signup",
            json={
                "email": email,
                "password": "TestPassw0rd!",
                "display_name": label.title(),
            },
        )
        assert response.status_code in (200, 201), (
            "signup failed: %s %s" % (response.status_code, response.get_json())
        )
        user = payload(response).get("user") or {}
        user_id = user.get("id") or user.get("uid")
        assert user_id, "signup returned no user id: %s" % (response.get_json(),)
        return api, user_id, email

    return _make


@pytest.fixture
def alice(make_user):
    return make_user("alice")


@pytest.fixture
def bob(make_user):
    return make_user("bob")


@pytest.fixture
def expense_group(alice):
    """An expense group created by alice. Returns (api, user_id, group_id)."""
    api, user_id, _ = alice
    response = api.post(
        "/api/v1/expenses/groups", json={"name": "Trip %s" % uuid.uuid4().hex[:6]}
    )
    assert response.status_code in (200, 201), response.get_json()
    group = payload(response).get("group") or payload(response)
    group_id = group.get("id")
    assert group_id, response.get_json()
    return api, user_id, group_id


@pytest.fixture
def group_of_two(expense_group, bob):
    """An expense group containing alice (owner) and bob.

    Returns (alice_api, alice_id, bob_api, bob_id, group_id).
    """
    alice_api, alice_id, group_id = expense_group
    bob_api, bob_id, bob_email = bob
    response = alice_api.post(
        "/api/v1/expenses/groups/%s/members" % group_id, json={"email": bob_email}
    )
    assert response.status_code in (200, 201), response.get_json()
    return alice_api, alice_id, bob_api, bob_id, group_id
