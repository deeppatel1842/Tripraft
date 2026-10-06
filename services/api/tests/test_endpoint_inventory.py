# Purpose: Regression tests for endpoint inventory, including success and failure behavior.
"""Live regressions for the broken-endpoint inventory, using real UUIDv7 IDs."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from conftest import payload
from app.expenses.models import Expense
from app.trips.models import ChatMessage, TripInvitation, TripMember
from app.core.db.connection import get_db_session
from app.trips.services.chat_service import ChatService
from app.scout.services.consent_gate import ConsentGate
from app.scout.services.crew_agent_service import CrewAgentService
from app.trips.services.trip_invite_service import InvitationService


@pytest.fixture
def trip(alice):
    api, user_id, _ = alice
    response = api.post('/api/v1/group-planner/groups', json={'name': 'Endpoint inventory'})
    assert response.status_code == 201, response.get_json()
    group = payload(response).get('group') or payload(response)
    return api, user_id, group['id']


@pytest.mark.parametrize('command', ['opt in', 'opt out', 'forget me'])
def test_scout_consent_is_applied_without_queueing(trip, monkeypatch, command):
    api, user_id, group_id = trip
    from app.core.workers.tasks.ai_tasks import process_scout_mention

    def unavailable(*args, **kwargs):
        pytest.fail('Consent commands must not depend on the worker queue')

    monkeypatch.setattr(process_scout_mention, 'delay', unavailable)
    response = api.post(
        f'/api/v1/group-planner/groups/{group_id}/messages',
        json={'content': f'@scout {command}'},
    )
    assert response.status_code == 201, response.get_json()
    with get_db_session() as session:
        consent = ConsentGate.check(session, group_id, user_id)
        assert consent.allowed is (command == 'opt in')
        assert consent.needs_prompt is False
    listed = api.get(f'/api/v1/group-planner/groups/{group_id}/messages')
    assert not any(
        message['content'].startswith('consent_')
        for message in payload(listed)['messages']
    )


def test_forget_me_still_erases_data_when_scout_is_disabled(trip, monkeypatch):
    api, user_id, group_id = trip
    with get_db_session() as session:
        ConsentGate.grant(session, group_id, user_id, 'GDPR', '127.0.0.1')
        session.commit()
    monkeypatch.setattr('app.core.config.Config.FF_SCOUT_AGENT', False)
    response = api.post(
        f'/api/v1/group-planner/groups/{group_id}/messages',
        json={'content': '@scout forget me'},
    )
    assert response.status_code == 201, response.get_json()
    with get_db_session() as session:
        consent = ConsentGate.check(session, group_id, user_id)
        assert not consent.allowed and not consent.needs_prompt


def test_unread_counts_follow_sends_reads_deletion_and_archival(trip, monkeypatch):
    api, user_id, group_id = trip
    from app.core.cache.redis import redis_client
    monkeypatch.setattr(redis_client, 'get', lambda key: '99')

    def count():
        response = api.get(f'/api/v1/group-planner/groups/{group_id}/unread-count')
        assert response.status_code == 200, response.get_json()
        return payload(response)['unread_count']

    def send(content):
        response = api.post(
            f'/api/v1/group-planner/groups/{group_id}/messages',
            json={'content': content},
        )
        assert response.status_code == 201, response.get_json()
        return payload(response)['id']

    assert count() == 0
    first_id = send('First message')
    assert count() == 1
    response = api.post(
        f'/api/v1/group-planner/groups/{group_id}/messages/read',
        json={'last_read_message_id': first_id},
    )
    assert response.status_code == 200, response.get_json()
    assert count() == 0
    second_id = send('Deleted message')
    assert count() == 1
    assert api.delete(f'/api/v1/group-planner/messages/{second_id}').status_code == 200
    assert count() == 0
    third_id = send('Archived message')
    assert count() == 1
    with get_db_session() as session:
        session.get(ChatMessage, third_id).is_archived = True
        session.commit()
    assert count() == 0


def test_equal_timestamp_read_receipts_cannot_move_backward(trip):
    _, user_id, group_id = trip
    first_id = UUID('01923456-789a-7000-8000-000000000001')
    second_id = UUID('01923456-789a-7000-8000-000000000002')
    with get_db_session() as session:
        same_time = datetime(2026, 1, 1)
        session.add_all([
            ChatMessage(id=message_id, group_id=group_id, sender_id=user_id,
                        content='Same timestamp', created_at=same_time)
            for message_id in (first_id, second_id)
        ])
        session.commit()
    assert ChatService.get_unread_count(group_id, user_id) == 2
    assert ChatService.mark_read(group_id, user_id, second_id)[0]
    assert ChatService.get_unread_count(group_id, user_id) == 0
    success, result = ChatService.mark_read(group_id, user_id, first_id)
    assert success
    assert result['last_read_message_id'] == second_id
    assert ChatService.get_unread_count(group_id, user_id) == 0


def test_crew_expense_uses_linked_group_and_uuid_payer(trip):
    api, user_id, group_id = trip
    linked = api.post(f'/api/v1/group-planner/groups/{group_id}/link-expense')
    assert linked.status_code == 200, linked.get_json()
    expense_group_id = payload(linked)['expense_group_id']
    with get_db_session() as session:
        success, result = CrewAgentService.process(
            session, group_id, UUID(user_id),
            '@crew add expense 40 for dinner split equally', None,
        )
        assert success, result
        session.commit()
    with get_db_session() as session:
        expense = session.query(Expense).filter_by(group_id=expense_group_id).one()
        assert expense.group_id != UUID(group_id)
        assert expense.paid_by == UUID(user_id)
        assert expense.amount == Decimal('40.00')


@pytest.mark.parametrize('expired', [False, True])
def test_trip_invitation_acceptance_checks_utc_expiry(trip, bob, expired):
    api, inviter_id, group_id = trip
    bob_api, bob_id, bob_email = bob
    sent, result = InvitationService.create_invitation(group_id, bob_email, inviter_id)
    assert sent, result
    invitation_id = result['invitation_id']
    with get_db_session() as session:
        invitation = session.get(TripInvitation, invitation_id)
        invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=-1 if expired else 1)
        session.commit()
    response = bob_api.post(f'/api/v1/group-planner/invitations/{invitation_id}/accept')
    assert response.status_code == (400 if expired else 200), response.get_json()
    with get_db_session() as session:
        invitation = session.get(TripInvitation, invitation_id)
        assert invitation.status == ('expired' if expired else 'accepted')
        member = session.query(TripMember).filter_by(group_id=group_id, user_id=bob_id).first()
        assert (member is not None and member.is_active) is (not expired)


def test_repeated_gp_invitation_keeps_a_valid_email_link(trip, bob, monkeypatch):
    api, _, group_id = trip
    _, _, bob_email = bob
    from app.notifications.email.smtp import email_service
    calls = []
    monkeypatch.setattr(email_service, 'send_invitation', lambda **kwargs: calls.append(kwargs) or True)
    responses = [api.post(
        '/api/v2/group-planner/invitations',
        json={'group_id': group_id, 'email': bob_email},
        follow_redirects=True,
    ) for _ in range(2)]
    for response in responses:
        assert response.status_code == 201, response.get_json()
    invitation_id = payload(responses[0])['id']
    assert UUID(invitation_id).version == 7
    assert len(calls) == 2
    assert all(call['invitation_token'] == invitation_id for call in calls)
    assert all(call['group_name'] == 'Endpoint inventory' for call in calls)


def test_users_password_and_session_deletion_use_the_authenticated_uuid(alice):
    api, user_id, email = alice
    changed = api.put('/api/v1/users/me/password', json={
        'current_password': 'TestPassw0rd!', 'new_password': 'ChangedPassw0rd!',
    })
    assert changed.status_code == 200, changed.get_json()
    login = api.post('/api/v1/auth/login', json={'email': email, 'password': 'ChangedPassw0rd!'})
    assert login.status_code == 200, login.get_json()
    assert payload(login)['user']['id'] == user_id
    assert api.delete('/api/v1/users/me/sessions').status_code == 200
    assert api.post('/api/v1/auth/refresh').status_code == 401


@pytest.mark.parametrize('path', [
    '/api/v1/trip-planner/cities?limit=x',
    '/api/v1/trip-planner/cities/search?q=Paris&limit=x',
    '/api/v1/auth/mega-bootstrap?recent_expenses_limit=x',
])
def test_malformed_limits_return_client_errors(alice, path):
    api, _, _ = alice
    response = api.get(path)
    assert response.status_code == 400, response.get_json()


def test_trip_generation_rejects_malformed_days(client):
    response = client.post(
        '/api/v1/trip-planner/generate', json={'city': 'Paris', 'days': 'x'},
    )
    assert response.status_code == 422, response.get_json()
