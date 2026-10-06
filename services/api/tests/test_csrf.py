# Purpose: Regression tests for csrf, including success and failure behavior.
"""Step 3 — CSRF must cover authenticated cookie operations.

The exemption was the prefix '/api/v1/auth/', which also covered
change-password, logout, logout-all and PUT /me. Those all act on a live
cookie session, so a cross-site form could drive them (audit P1-13).
"""
import uuid

import pytest
from conftest import ApiClient, payload


def _signup(app, label="csrf"):
    """Returns (csrf-aware client, raw client sharing its cookies, email)."""
    api = ApiClient(app)
    email = "%s_%s@example.test" % (label, uuid.uuid4().hex[:10])
    response = api.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "TestPassw0rd!", "display_name": "C"},
    )
    assert response.status_code in (200, 201), response.get_json()
    return api, api.raw, email


# ---------------------------------------------------------------------------
# Authenticated operations are protected
# ---------------------------------------------------------------------------

def test_change_password_requires_csrf_header(app):
    """The highest-value target the blanket exemption was covering."""
    api, raw, _ = _signup(app, "cp")
    response = raw.post(
        "/api/v1/auth/change-password",
        json={"current_password": "TestPassw0rd!", "new_password": "Another1Pass!"},
    )
    assert response.status_code == 403, response.get_json()


def test_change_password_succeeds_with_csrf_header(app):
    api, _, _ = _signup(app, "cp2")
    response = api.post(
        "/api/v1/auth/change-password",
        json={"current_password": "TestPassw0rd!", "new_password": "Another1Pass!"},
    )
    assert response.status_code == 200, response.get_json()


def test_logout_requires_csrf_header(app):
    api, raw, _ = _signup(app, "lo")
    assert raw.post("/api/v1/auth/logout").status_code == 403


def test_logout_all_requires_csrf_header(app):
    api, raw, _ = _signup(app, "loa")
    assert raw.post("/api/v1/auth/logout-all").status_code == 403


def test_profile_update_requires_csrf_header(app):
    api, raw, _ = _signup(app, "pu")
    response = raw.put("/api/v1/auth/me", json={"display_name": "Hijacked"})
    assert response.status_code == 403


def test_refresh_requires_csrf_header_while_the_session_is_live(app):
    """Refresh rotates a live session, so it is not pre-auth."""
    api, raw, _ = _signup(app, "rf")
    assert raw.post("/api/v1/auth/refresh").status_code == 403
    assert api.post("/api/v1/auth/refresh").status_code == 200


def test_group_planner_invitation_routes_are_protected(app):
    """They were exempted as "pre-auth", but every one carries @require_auth."""
    api, raw, _ = _signup(app, "gpi")
    response = raw.post(
        "/api/v1/group-planner/invitations",
        json={"group_id": str(uuid.uuid4()), "email": "x@example.test"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Genuinely pre-auth endpoints stay reachable
# ---------------------------------------------------------------------------

def test_signup_needs_no_csrf_header(app):
    raw = ApiClient(app).raw
    response = raw.post(
        "/api/v1/auth/signup",
        json={
            "email": "pre_%s@example.test" % uuid.uuid4().hex[:10],
            "password": "TestPassw0rd!",
            "display_name": "Pre",
        },
    )
    assert response.status_code in (200, 201), response.get_json()


def test_login_needs_no_csrf_header(app):
    api, _, email = _signup(app, "li")
    raw = ApiClient(app).raw
    response = raw.post(
        "/api/v1/auth/login", json={"email": email, "password": "TestPassw0rd!"}
    )
    assert response.status_code == 200, response.get_json()


def test_check_email_needs_no_csrf_header(app):
    raw = ApiClient(app).raw
    response = raw.post(
        "/api/v1/auth/check-email", json={"email": "nobody@example.test"}
    )
    assert response.status_code in (200, 404), response.get_json()


def test_refresh_works_when_the_access_token_has_expired(app):
    """The expiry case still has to work: no access_token cookie means no
    CSRF check, which is what lets a client recover its session."""
    api, raw, _ = _signup(app, "exp")
    raw.delete_cookie("access_token")
    raw.delete_cookie("csrf_token")
    assert raw.post("/api/v1/auth/refresh").status_code == 200
