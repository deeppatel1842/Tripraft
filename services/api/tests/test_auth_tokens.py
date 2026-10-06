# Purpose: Regression tests for auth tokens, including success and failure behavior.
"""Step 3 — refresh tokens must never be readable in the database."""
import hashlib
import uuid

from conftest import ApiClient, payload

from app.expenses.models import UserSession
from app.auth.models import User
from app.auth.security.jwt import (create_email_verification_token,
                                         hash_refresh_token)
from app.core.db.connection import get_db_session
from app.auth.services.auth_service import AuthService


def _sessions_for(user_id):
    with get_db_session() as session:
        rows = session.query(UserSession).filter(
            UserSession.user_id == uuid.UUID(str(user_id))
        ).all()
        return [row.refresh_token for row in rows]


def _signup(app, label="tok"):
    api = ApiClient(app)
    email = "%s_%s@example.test" % (label, uuid.uuid4().hex[:10])
    response = api.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "TestPassw0rd!", "display_name": "Tok"},
    )
    assert response.status_code in (200, 201), response.get_json()
    body = payload(response)
    user_id = (body.get("user") or {}).get("id")
    refresh = body.get("refresh_token")
    return api, user_id, email, refresh


def test_signup_stores_a_digest_not_the_token(app):
    """P0-14: the raw refresh token was written straight into the column."""
    _, user_id, _, refresh = _signup(app)
    stored = _sessions_for(user_id)
    assert stored, "no session row was created"
    assert refresh, "signup did not return a refresh token"

    assert refresh not in stored, "the raw refresh token is in the database"
    assert hash_refresh_token(refresh) in stored


def test_stored_value_is_sha256_hex(app):
    _, user_id, _, refresh = _signup(app)
    stored = _sessions_for(user_id)[0]
    assert stored == hashlib.sha256(refresh.encode("utf-8")).hexdigest()
    assert len(stored) == 64


def test_login_stores_a_digest(app):
    api, user_id, email, _ = _signup(app, "login")
    fresh = ApiClient(app)
    response = fresh.post(
        "/api/v1/auth/login", json={"email": email, "password": "TestPassw0rd!"}
    )
    assert response.status_code == 200, response.get_json()
    refresh = payload(response).get("refresh_token")
    assert refresh

    stored = _sessions_for(user_id)
    assert refresh not in stored
    assert hash_refresh_token(refresh) in stored


def test_refresh_round_trip_still_works(app):
    """Hashing must not break the flow it protects."""
    api, user_id, _, _ = _signup(app, "rt")
    response = api.post("/api/v1/auth/refresh")
    assert response.status_code == 200, response.get_json()

    rotated = payload(response).get("refresh_token")
    assert rotated, response.get_json()

    stored = _sessions_for(user_id)
    assert rotated not in stored, "rotation wrote the raw token"
    assert hash_refresh_token(rotated) in stored


def test_rotation_invalidates_the_previous_token(app):
    api, user_id, _, original = _signup(app, "rot")
    first = api.post("/api/v1/auth/refresh")
    assert first.status_code == 200

    stored = _sessions_for(user_id)
    assert hash_refresh_token(original) not in stored


def test_logout_removes_the_session(app):
    api, user_id, _, _ = _signup(app, "out")
    assert _sessions_for(user_id)

    response = api.post("/api/v1/auth/logout")
    assert response.status_code in (200, 204), response.get_json()
    assert _sessions_for(user_id) == []


def test_email_verification_persists_its_audit_timestamp(app):
    """P1-12: verification time must be a mapped, committed column."""
    _, user_id, email, _ = _signup(app, "verify")
    token = create_email_verification_token(user_id, email)

    success, result = AuthService.verify_email(token)
    assert success, result

    with get_db_session() as session:
        user = session.get(User, user_id)
        assert user is not None
        assert user.email_verified
        assert user.email_verified_at is not None
