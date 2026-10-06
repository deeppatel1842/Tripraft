# Purpose: Regression tests for money concurrency, including success and failure behavior.
"""Money validation must use balances and records locked by its transaction."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import UUID

import pytest

from conftest import payload
from app.expenses.models import Expense, ExpenseSplit, GroupBalance, Settlement
from app.core.db.connection import get_db
from app.expenses.services import money_lock
from app.expenses.services.expense_service import ExpenseServiceSQL
from app.expenses.services.settlement_service import SettlementServiceSQL


def _expense(group_of_two, amount=60):
    api, alice, _, bob, group = group_of_two
    response = api.post('/api/v1/expenses', json={
        'description': 'Concurrent ledger', 'amount': amount,
        'group_id': group, 'paid_by': alice, 'split_type': 'equal',
    })
    assert response.status_code == 201, response.get_json()
    return payload(response)['expense']['id']


def _synchronize_lock(monkeypatch, module):
    """Make both operations arrive at the lock with their initial reads done."""
    barrier = Barrier(2)
    original = money_lock.lock_group

    def acquire(session, group_id):
        barrier.wait(timeout=10)
        return original(session, group_id)

    monkeypatch.setattr(module, 'lock_group', acquire)


def _race(*calls):
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(call) for call in calls]
        return [future.result(timeout=20) for future in pending]


def _balances(group_id):
    with get_db() as session:
        return {
            str(row.user_id): row.balance
            for row in session.query(GroupBalance).filter_by(group_id=group_id)
        }


def test_concurrent_settlements_cannot_both_spend_the_same_debt(group_of_two, monkeypatch):
    from app.expenses.services import settlement_service

    _, alice, _, bob, group = group_of_two
    _expense(group_of_two)
    _synchronize_lock(monkeypatch, settlement_service)
    results = _race(*[
        lambda: SettlementServiceSQL.create_settlement(bob, group, bob, alice, Decimal('20'))
        for _ in range(2)
    ])
    assert sorted(success for success, _ in results) == [False, True], results
    rejected = next(result for success, result in results if not success)
    assert 'cannot exceed' in rejected['error']
    assert _balances(group) == {alice: Decimal('10'), bob: Decimal('-10')}
    with get_db() as session:
        assert session.query(Settlement).filter_by(group_id=group, is_deleted=False).count() == 1


@pytest.mark.parametrize('kind', ['expense', 'settlement'])
def test_concurrent_delete_reverses_money_once(group_of_two, monkeypatch, kind):
    _, alice, _, bob, group = group_of_two
    expense_id = _expense(group_of_two)
    if kind == 'settlement':
        success, result = SettlementServiceSQL.create_settlement(bob, group, bob, alice, Decimal('30'))
        assert success, result
        record_id = result['settlement']['id']
        delete = lambda: SettlementServiceSQL.delete_settlement(record_id, UUID(bob))
        expected = {alice: Decimal('30'), bob: Decimal('-30')}
    else:
        delete = lambda: ExpenseServiceSQL.delete_expense(expense_id, UUID(alice))
        expected = {alice: Decimal('0'), bob: Decimal('0')}
    _synchronize_lock(monkeypatch, money_lock)
    results = _race(delete, delete)
    assert sorted(success for success, _ in results) == [False, True], results
    assert _balances(group) == expected


def test_concurrent_edits_apply_the_latest_stored_expense(group_of_two, monkeypatch):
    _, alice, _, bob, group = group_of_two
    expense_id = _expense(group_of_two)
    _synchronize_lock(monkeypatch, money_lock)
    results = _race(
        lambda: ExpenseServiceSQL.update_expense(expense_id, UUID(alice), amount=Decimal('80')),
        lambda: ExpenseServiceSQL.update_expense(expense_id, UUID(alice), amount=Decimal('100')),
    )
    assert all(success for success, _ in results), results
    with get_db() as session:
        expense = session.get(Expense, expense_id)
        amount = expense.amount
        assert amount in (Decimal('80'), Decimal('100'))
        splits = session.query(ExpenseSplit).filter_by(expense_id=expense_id).all()
        assert sum((row.amount for row in splits), Decimal('0')) == amount
    assert _balances(group) == {alice: amount / 2, bob: -amount / 2}
