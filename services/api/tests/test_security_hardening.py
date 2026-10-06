# Purpose: Regression tests for security hardening, including success and failure behavior.
"""Phase 1 trust-boundary regressions."""
import uuid

import pytest
from flask import Flask, g

from app.core.middleware import inject_request_id
from app.core.config import Config, ProductionConfig
from app.core.rate_limiter import _get_rate_limit_key
from app.notifications.services.email_service import EmailService


def test_rate_limit_ignores_spoofed_forwarded_for(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(Config, 'TRUSTED_PROXY_IPS', [])
    with app.test_request_context(
        '/', headers={'X-Forwarded-For': '203.0.113.7'},
        environ_base={'REMOTE_ADDR': '198.51.100.4'},
    ):
        assert _get_rate_limit_key() == 'ip:198.51.100.4'


def test_rate_limit_uses_forwarded_for_from_a_trusted_proxy(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(Config, 'TRUSTED_PROXY_IPS', ['10.0.0.0/8'])
    with app.test_request_context(
        '/', headers={'X-Forwarded-For': '203.0.113.7, 10.0.0.10'},
        environ_base={'REMOTE_ADDR': '10.0.0.10'},
    ):
        assert _get_rate_limit_key() == 'ip:203.0.113.7'


def test_invalid_client_correlation_ids_are_replaced():
    app = Flask(__name__)
    with app.test_request_context(
        '/', environ_overrides={
            # Werkzeug's request builder rejects newline headers itself.
            # Inject the raw WSGI values to exercise our middleware check.
            'HTTP_X_REQUEST_ID': 'x\r\nforged: header',
            'HTTP_X_TRACE_ID': 'x' * 65,
        },
    ):
        inject_request_id()
        assert g.request_id != 'x\r\nforged: header'
        assert len(g.request_id) <= 64
        assert g.trace_id == g.request_id[:12]


def test_valid_client_correlation_ids_are_preserved():
    app = Flask(__name__)
    request_id = 'request_' + uuid.uuid4().hex
    with app.test_request_context('/', headers={'X-Request-ID': request_id}):
        inject_request_id()
        assert g.request_id == request_id


def test_route_viewer_requires_authentication(app):
    response = app.test_client().get('/api/routes')
    assert response.status_code == 401


def test_invitation_html_escapes_group_and_inviter_names(monkeypatch):
    service = EmailService()
    captured = {}

    def capture(*args, **kwargs):
        captured['html'] = args[2]
        return True

    monkeypatch.setattr(service, 'send_email', capture)
    service.send_group_invitation(
        'person@example.test', '<img src=x onerror=alert(1)>',
        '<script>alert(1)</script>', 'safe-id',
    )

    assert '<script>alert(1)</script>' not in captured['html']
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in captured['html']
    assert '<img src=x onerror=alert(1)>' not in captured['html']


def test_production_requires_configured_admins(monkeypatch):
    monkeypatch.setattr(ProductionConfig, 'ADMIN_EMAILS', [])
    monkeypatch.setattr(ProductionConfig, 'SECRET_KEY', 'not-the-development-secret')
    monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379/0')
    with pytest.raises(ValueError, match='ADMIN_EMAILS'):
        ProductionConfig.validate()
