# Purpose: Regression tests for phase1 contracts, including success and failure behavior.
"""Phase 1 API-contract, invitation, and chat regressions."""
import uuid

import pytest
from flask import Flask

from conftest import ApiClient, payload
from app.core.apiutils.responses import success_response
from app.core.apiutils.responses import success_response
from app.expenses.models import GroupMember
from app.trips.models import TripMember
from app.core.db.connection import get_db_session
from app.core.schemas.auth import SignupSchema
from app.core.schemas.invitations import InviteMemberSchema
from app.trips.services.chat_service import ChatService
from app.expenses.services.expense_invite_service import InvitationServiceSQL
from app.trips.services.trip_invite_service import InvitationService


def _travel_group(api):
    response = api.post(
        '/api/v1/group-planner/groups',
        json={'name': 'Contracts %s' % uuid.uuid4().hex[:8]},
    )
    assert response.status_code in (200, 201), response.get_json()
    return (payload(response).get('group') or payload(response))['id']


def test_success_response_honors_data_message_and_status(app):
    with app.test_request_context('/'):
        response, status = success_response(data={'group': 'result'}, message='Group cloned', status_code=201)
    assert status == 201
    assert response.get_json()['data'] == {'group': 'result'}
    assert response.get_json()['message'] == 'Group cloned'


def test_signup_schema_accepts_and_validates_documented_profile_fields():
    validated = SignupSchema().load({
        'email': 'profile@example.test',
        'password': 'TestPassw0rd!',
        'phone': '+15551234567',
        'default_currency': 'eur',
    })
    assert validated['phone'] == '+15551234567'
    assert validated['default_currency'] == 'eur'


def test_signup_persists_documented_phone_and_currency(app):
    api = ApiClient(app)
    response = api.post(
        '/api/v1/auth/signup',
        json={
            'email': 'profile_%s@example.test' % uuid.uuid4().hex[:8],
            'password': 'TestPassw0rd!',
            'display_name': 'Profile',
            'phone': '+15551234567',
            'default_currency': 'eur',
        },
    )
    assert response.status_code in (200, 201), response.get_json()
    user = (payload(response).get('user') or {})
    assert user['phone'] == '+15551234567'
    assert user['default_currency'] == 'EUR'


def test_invitation_schema_normalizes_email_case():
    assert InviteMemberSchema().load({'email': ' User@Example.Test '})['email'] == 'user@example.test'


def test_expense_invitation_reactivates_an_inactive_member(group_of_two):
    alice_api, alice_id, bob_api, bob_id, group_id = group_of_two
    bob_email = 'unused@example.test'
    with get_db_session() as session:
        member = session.query(GroupMember).filter_by(group_id=group_id, user_id=bob_id).one()
        member.is_active = False
        session.commit()
        bob_email = member.user.email

    sent, invitation_result = InvitationServiceSQL.send_invitation(group_id, bob_email.upper(), alice_id)
    assert sent, invitation_result
    invitation_id = invitation_result['invitation']['id']

    accepted, acceptance_result = InvitationServiceSQL.accept_invitation(invitation_id, bob_id)
    assert accepted, acceptance_result
    with get_db_session() as session:
        member = session.query(GroupMember).filter_by(group_id=group_id, user_id=bob_id).one()
        assert member.is_active


def test_trip_invitation_reactivates_an_inactive_member(alice, bob):
    alice_api, alice_id, _ = alice
    _, bob_id, bob_email = bob
    group_id = _travel_group(alice_api)
    with get_db_session() as session:
        session.add(TripMember(group_id=group_id, user_id=bob_id, role='member', is_active=False))
        session.commit()

    sent, invitation_result = InvitationService.create_invitation(group_id, bob_email.upper(), alice_id)
    assert sent, invitation_result
    accepted, acceptance_result = InvitationService.accept_invitation(
        invitation_result['invitation_id'], bob_id, bob_email,
    )
    assert accepted, acceptance_result
    with get_db_session() as session:
        member = session.query(TripMember).filter_by(group_id=group_id, user_id=bob_id).one()
        assert member.is_active


def test_group_planner_invitation_uses_the_real_email_service(alice, bob, monkeypatch):
    alice_api, _, _ = alice
    _, _, bob_email = bob
    group_id = _travel_group(alice_api)
    calls = []
    from app.notifications.email.smtp import email_service
    monkeypatch.setattr(email_service, 'send_invitation', lambda **kwargs: calls.append(kwargs) or True)

    response = alice_api.post(
        '/api/v1/group-planner/invitations',
        json={'group_id': group_id, 'email': bob_email},
    )
    assert response.status_code in (200, 201), response.get_json()
    assert calls and calls[0]['to_email'] == bob_email
    assert calls[0]['invitation_type'] == 'trip'


def test_unread_count_without_a_receipt_counts_uuid_messages(alice):
    api, user_id, _ = alice
    group_id = _travel_group(api)
    sent, _ = ChatService.send_message(group_id, user_id, 'Unread UUID message')
    assert sent
    assert ChatService.get_unread_count(group_id, user_id) == 1


def test_socketio_failure_is_fatal_when_enabled_in_production(monkeypatch):
    from app.core.factory import _init_socketio
    from app.trips.realtime import socketio_ext

    app = Flask(__name__)
    app.config.update(FLASK_ENV='production', SOCKETIO_ENABLED=True)

    def unavailable(_app):
        raise ImportError('simulated missing flask-socketio')

    monkeypatch.setattr(socketio_ext, 'init_socketio', unavailable)
    with pytest.raises(RuntimeError, match='SocketIO initialization failed'):
        _init_socketio(app)


def test_non_member_payer_error_is_generic(group_of_two):
    api, _, _, _, group_id = group_of_two
    response = api.post(
        '/api/v1/expenses',
        json={
            'description': 'Bad payer',
            'amount': 1,
            'group_id': group_id,
            'paid_by': str(uuid.uuid4()),
            'split_type': 'equal',
        },
    )
    assert response.status_code == 400, response.get_json()
    assert response.get_json()['error']['message'] == 'Payer must be an active group member'
