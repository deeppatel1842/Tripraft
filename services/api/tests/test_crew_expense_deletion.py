# Purpose: Regression tests for crew expense deletion, including success and failure behavior.
"""P2-14: confirmed Crew deletion must preserve ledger and authorization rules."""
import json
from hashlib import md5
from fnmatch import fnmatch
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from conftest import payload
from app.scout.routes import ai_confirm
from app.expenses.models import Expense, ExpenseHistory, GroupBalance, GroupMember
from app.trips.models import TravelGroup, TripMember
from app.core.db.connection import get_db_session
from app.scout.services.crew_agent_service import CrewAgentService
from app.expenses.services.expense_service import ExpenseServiceSQL


class ConfirmationStore:
    available = True

    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        assert ex and ex > 0
        self.values[key] = value
        return True

    def getdel(self, key):
        return self.values.pop(key, None)

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)

    def delete_pattern(self, pattern):
        matches = [key for key in self.values if fnmatch(key, pattern)]
        for key in matches:
            self.values.pop(key)
        return len(matches)


@pytest.fixture
def ledger_trip(group_of_two, monkeypatch):
    owner_api, owner, member_api, member, ledger = group_of_two
    response = owner_api.post('/api/v1/group-planner/groups', json={
        'name': 'Crew deletion trip', 'destination': 'Kyoto',
    })
    assert response.status_code == 201, response.get_json()
    trip = (payload(response).get('group') or payload(response))['id']
    with get_db_session() as session:
        session.get(TravelGroup, trip).expense_group_id = UUID(ledger)
        session.add(TripMember(group_id=UUID(trip), user_id=UUID(member), role='member'))
        session.commit()
    store = ConfirmationStore()
    monkeypatch.setattr(ai_confirm, 'redis_client', store)
    return dict(owner_api=owner_api, owner=owner, member_api=member_api,
                member=member, ledger=ledger, trip=trip, store=store)


def create_expense(context, creator='member', description='Dinner', group_id=None):
    response = context[creator + '_api'].post('/api/v1/expenses', json={
        'description': description, 'amount': 100, 'paid_by': context['owner'],
        'group_id': group_id or context['ledger'], 'split_type': 'exact',
        'splits': [
            {'user_id': context['owner'], 'amount': 25},
            {'user_id': context['member'], 'amount': 75},
        ],
    })
    assert response.status_code == 201, response.get_json()
    return payload(response)['expense']['id']


def run_command(context, content='@crew delete expense Dinner', actor='member'):
    with get_db_session() as session:
        return CrewAgentService.process(session, context['trip'], context[actor], content, context['store'])


def prepare(context, actor='member', description='Dinner'):
    ok, result = run_command(context, '@crew delete expense ' + description, actor)
    assert ok and result['response_type'] == 'confirmation_card', result
    return result['metadata']['pending_key']


def confirm(context, key, actor='member', action='confirm'):
    return context[actor + '_api'].post(
        f'/api/v1/group-planner/groups/{context["trip"]}/ai/confirm',
        json={'action': action, 'pending_key': key},
    )


def snapshot(context, expense_id):
    with get_db_session() as session:
        expense = session.get(Expense, expense_id)
        return {
            'deleted': expense.is_deleted,
            'deleted_by': str(expense.deleted_by) if expense.deleted_by else None,
            'splits': {str(split.user_id): split.amount for split in expense.splits},
            'balances': {str(row.user_id): row.balance for row in session.query(GroupBalance).filter_by(
                group_id=context['ledger'],
            ).all()},
            'deletions': session.query(ExpenseHistory).filter_by(
                expense_id=expense_id, action='deleted',
            ).count(),
        }


@pytest.mark.parametrize('actor', ['member', 'owner'])
def test_creator_and_ledger_owner_can_confirm_exact_balance_reversal(ledger_trip, actor):
    ctx = ledger_trip
    expense = create_expense(ctx)
    before = snapshot(ctx, expense)
    assert before['balances'][ctx['owner']] == Decimal('75.00')
    assert before['balances'][ctx['member']] == Decimal('-75.00')
    key = prepare(ctx, actor)
    assert snapshot(ctx, expense) == before
    response = confirm(ctx, key, actor)
    assert response.status_code == 200, response.get_json()
    assert payload(response)['expense_group_id'] == ctx['ledger']
    after = snapshot(ctx, expense)
    assert after['deleted'] and after['deleted_by'] == ctx[actor]
    assert after['deletions'] == 1 and after['splits'] == before['splits']
    assert all(amount == Decimal('0.00') for amount in after['balances'].values())
    assert confirm(ctx, key, actor).status_code == 404
    assert snapshot(ctx, expense) == after


def test_another_member_cannot_offer_or_execute_deletion(ledger_trip):
    ctx = ledger_trip
    expense = create_expense(ctx, creator='owner')
    before = snapshot(ctx, expense)
    ok, result = run_command(ctx)
    assert not ok and result['response_type'] == 'error_text'
    assert not ctx['store'].values
    key = f'crew:confirm:{ctx["trip"]}:{ctx["member"]}:{uuid4()}'
    ctx['store'].values[key] = json.dumps(dict(
        entity_type='expense', entity_id=expense, entity_name='Dinner', expense_group_id=ctx['ledger'],
    ))
    assert confirm(ctx, key).status_code == 400
    assert snapshot(ctx, expense) == before


@pytest.mark.parametrize('action', ['cancel', 'expired'])
def test_cancelled_or_expired_confirmation_never_changes_money(ledger_trip, action):
    ctx = ledger_trip
    expense = create_expense(ctx)
    before = snapshot(ctx, expense)
    key = prepare(ctx)
    if action == 'expired':
        ctx['store'].values.pop(key)
        response = confirm(ctx, key)
        assert response.status_code == 404
    else:
        assert confirm(ctx, key, action='cancel').status_code == 200
        assert confirm(ctx, key).status_code == 404
    assert snapshot(ctx, expense) == before


@pytest.mark.parametrize('foreign_type', ['other-ledger', 'personal'])
def test_foreign_or_personal_expense_cannot_be_deleted_through_trip(ledger_trip, foreign_type):
    ctx = ledger_trip
    if foreign_type == 'other-ledger':
        response = ctx['owner_api'].post('/api/v1/expenses/groups', json={'name': 'Other ledger'})
        other = (payload(response).get('group') or payload(response))['id']
        response = ctx['owner_api'].post('/api/v1/expenses', json={
            'description': 'Foreign dinner', 'amount': 10, 'group_id': other,
            'paid_by': ctx['owner'], 'split_type': 'equal',
        })
    else:
        response = ctx['owner_api'].post('/api/v1/expenses', json={
            'description': 'Foreign dinner', 'amount': 10, 'paid_by': ctx['owner'],
        })
    assert response.status_code == 201, response.get_json()
    expense = payload(response)['expense']['id']
    before = snapshot(ctx, expense)
    ok, _ = run_command(ctx, '@crew delete expense Foreign', 'owner')
    assert not ok
    key = f'crew:confirm:{ctx["trip"]}:{ctx["owner"]}:{uuid4()}'
    ctx['store'].values[key] = json.dumps(dict(
        entity_type='expense', entity_id=expense, entity_name='Foreign dinner', expense_group_id=ctx['ledger'],
    ))
    assert confirm(ctx, key, 'owner').status_code == 400
    assert snapshot(ctx, expense) == before


@pytest.mark.parametrize('change', ['ledger-membership', 'trip-membership', 'trip-link', 'creator'])
def test_confirmation_rechecks_permissions_and_trip_link(ledger_trip, change):
    ctx = ledger_trip
    expense = create_expense(ctx)
    key = prepare(ctx)
    with get_db_session() as session:
        if change == 'ledger-membership':
            session.query(GroupMember).filter_by(group_id=ctx['ledger'], user_id=ctx['member']).one().is_active = False
        elif change == 'trip-membership':
            session.query(TripMember).filter_by(group_id=ctx['trip'], user_id=ctx['member']).one().is_active = False
        elif change == 'trip-link':
            session.get(TravelGroup, ctx['trip']).expense_group_id = None
        else:
            session.get(Expense, expense).created_by = UUID(ctx['owner'])
        session.commit()
    before = snapshot(ctx, expense)
    assert confirm(ctx, key).status_code == (403 if change == 'trip-membership' else 400)
    assert snapshot(ctx, expense) == before


def test_previously_deleted_expense_is_not_reversed_twice(ledger_trip):
    ctx = ledger_trip
    expense = create_expense(ctx)
    key = prepare(ctx)
    assert ctx['member_api'].delete('/api/v1/expenses/' + expense).status_code == 200
    before = snapshot(ctx, expense)
    assert confirm(ctx, key).status_code == 400
    assert snapshot(ctx, expense) == before and before['deletions'] == 1


def test_duplicate_descriptions_select_the_persisted_uuid(ledger_trip):
    ctx = ledger_trip
    first, second = create_expense(ctx), create_expense(ctx)
    ok, result = run_command(ctx)
    assert ok and result['response_type'] == 'question_card'
    assert result['metadata']['options'] == ['1. Dinner', '2. Dinner']
    state_key = f'crew:conv:{ctx["trip"]}:{ctx["member"]}'
    candidates = json.loads(ctx['store'].get(state_key))['selection']['candidates']
    selected = candidates[1]['id']
    ok, card = run_command(ctx, '2. Dinner')
    assert ok and card['metadata']['entity_id'] == selected
    assert confirm(ctx, card['metadata']['pending_key']).status_code == 200
    assert snapshot(ctx, selected)['deleted']
    other = first if selected == second else second
    assert not snapshot(ctx, other)['deleted']


def test_stale_selection_does_not_offer_a_confirmation(ledger_trip):
    ctx = ledger_trip
    create_expense(ctx)
    create_expense(ctx)
    run_command(ctx)
    state_key = f'crew:conv:{ctx["trip"]}:{ctx["member"]}'
    selected = json.loads(ctx['store'].get(state_key))['selection']['candidates'][1]['id']
    assert ctx['member_api'].delete('/api/v1/expenses/' + selected).status_code == 200
    ok, result = run_command(ctx, '2')
    assert not ok and result['response_type'] == 'error_text'
    assert not any(key.startswith('crew:confirm:') for key in ctx['store'].values)


def test_each_card_has_its_own_target_and_other_users_cannot_consume_it(ledger_trip):
    ctx = ledger_trip
    first = create_expense(ctx, description='Breakfast')
    second = create_expense(ctx, description='Lunch')
    first_key = prepare(ctx, description='Breakfast')
    second_key = prepare(ctx, description='Lunch')
    assert first_key != second_key
    assert confirm(ctx, first_key, 'owner').status_code == 400
    assert ctx['store'].get(first_key)
    assert confirm(ctx, first_key).status_code == 200
    assert snapshot(ctx, first)['deleted'] and not snapshot(ctx, second)['deleted']
    assert ctx['store'].get(second_key)
    assert confirm(ctx, second_key).status_code == 200
    assert all(amount == 0 for amount in snapshot(ctx, second)['balances'].values())


@pytest.mark.parametrize('failure', ['unavailable', 'write-failed'])
def test_no_expense_confirmation_without_durable_state(ledger_trip, monkeypatch, failure):
    ctx = ledger_trip
    expense = create_expense(ctx)
    before = snapshot(ctx, expense)
    if failure == 'unavailable':
        ctx['store'].available = False
    else:
        monkeypatch.setattr(ctx['store'], 'set', lambda *args, **kwargs: False)
    ok, result = run_command(ctx)
    assert not ok and result['response_type'] == 'error_text'
    assert snapshot(ctx, expense) == before


def test_database_search_failure_is_not_reported_as_a_missing_expense(ledger_trip, monkeypatch):
    def fail(*args):
        raise SQLAlchemyError('Database unavailable')
    monkeypatch.setattr(CrewAgentService, '_deletable_expenses', fail)
    ok, result = run_command(ledger_trip)
    assert not ok and result['response_type'] == 'error_text'
    assert 'not found' not in result['content'].lower()
    assert 'something went wrong' in result['content'].lower()


def test_locked_expense_service_rejects_the_wrong_confirmed_ledger(ledger_trip):
    ctx = ledger_trip
    expense = create_expense(ctx)
    before = snapshot(ctx, expense)
    ok, result = ExpenseServiceSQL.delete_expense(expense, ctx['member'], expected_group_id=str(uuid4()))
    assert not ok and 'does not belong' in result['error']
    assert snapshot(ctx, expense) == before


def test_confirmed_deletion_invalidates_warmed_server_money_caches(ledger_trip, monkeypatch):
    from app.core.cache import redis as cache_module
    ctx = ledger_trip
    create_expense(ctx)
    monkeypatch.setattr(cache_module, 'redis_client', ctx['store'])
    endpoints = [
        ('gp_groups:expense_summary', f'/api/v1/group-planner/groups/{ctx["trip"]}/expense-summary'),
        ('expenses:group', f'/api/v1/expenses/group/{ctx["ledger"]}'),
        ('exp_groups:full', f'/api/v1/expenses/groups/{ctx["ledger"]}/full'),
        ('settlements:balances', f'/api/v1/expenses/settlements/group/{ctx["ledger"]}/balances'),
    ]
    keys = []
    for prefix, path in endpoints:
        response = ctx['owner_api'].get(path)
        assert response.status_code == 200, response.get_json()
        # Seed real response snapshots in the existing private cache contract.
        # Tuple-returning views currently skip automatic cache population.
        cache_key = prefix + ':' + md5(f'{path}::{ctx["owner"]}'.encode()).hexdigest()[:12]
        ctx['store'].set(cache_key, json.dumps({'_body': response.get_data(as_text=True)}), ex=60)
        keys.append(cache_key)
        cached = ctx['owner_api'].get(path)
        assert cached.headers['X-Cache'] == 'HIT'
    assert payload(ctx['owner_api'].get(endpoints[0][1]))['total_spent'] == 100
    assert confirm(ctx, prepare(ctx)).status_code == 200
    assert all(ctx['store'].get(key) is None for key in keys)
    responses = [ctx['owner_api'].get(path) for _, path in endpoints]
    for response in responses:
        assert response.status_code == 200, response.get_json()
        assert response.headers.get('X-Cache') != 'HIT'
    assert payload(responses[0])['total_spent'] == 0
    assert payload(responses[1])['expenses'] == []
    assert all(row['balance'] == 0 for row in payload(responses[3])['balances'])
