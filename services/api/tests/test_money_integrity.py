# Purpose: Regression tests for money integrity, including success and failure behavior.
"""Phase 1 — expense-ledger invariants.

These tests protect the properties that make an expense group trustworthy:
every expense split balances to zero, member identities are valid and unique,
and an edit cannot erase an existing debt.
"""
import uuid

import pytest

from conftest import payload
from app.expenses.models import GroupBalance, Settlement
from app.core.db.connection import get_db


def _split_map(expense):
    return {
        str(split["user_id"]): float(split["amount"])
        for split in expense["splits"]
    }


def _create_exact(api, group_id, payer_id, alice_id, bob_id):
    response = api.post(
        "/api/v1/expenses",
        json={
            "description": "Dinner",
            "amount": 100.0,
            "group_id": group_id,
            "paid_by": payer_id,
            "split_type": "exact",
            "splits": [
                {"user_id": alice_id, "amount": 25.0},
                {"user_id": bob_id, "amount": 75.0},
            ],
        },
    )
    assert response.status_code == 201, response.get_json()
    return payload(response)["expense"]


def test_rejects_exact_splits_that_do_not_equal_expense(group_of_two):
    api, alice_id, _, bob_id, group_id = group_of_two
    response = api.post(
        "/api/v1/expenses",
        json={
            "description": "Unbalanced dinner",
            "amount": 100.0,
            "group_id": group_id,
            "split_type": "exact",
            "splits": [
                {"user_id": alice_id, "amount": 30.0},
                {"user_id": bob_id, "amount": 50.0},
            ],
        },
    )
    assert response.status_code == 400, response.get_json()
    assert "add up" in response.get_json()["error"]["message"].lower()


def test_rejects_duplicate_and_non_member_split_users(group_of_two):
    api, alice_id, _, _, group_id = group_of_two
    duplicate = api.post(
        "/api/v1/expenses",
        json={
            "description": "Duplicate split",
            "amount": 20.0,
            "group_id": group_id,
            "split_type": "exact",
            "splits": [
                {"user_id": alice_id, "amount": 10.0},
                {"user_id": alice_id, "amount": 10.0},
            ],
        },
    )
    assert duplicate.status_code == 400, duplicate.get_json()
    assert "only once" in duplicate.get_json()["error"]["message"].lower()

    non_member = api.post(
        "/api/v1/expenses",
        json={
            "description": "Unknown member",
            "amount": 20.0,
            "group_id": group_id,
            "split_type": "exact",
            "splits": [
                {"user_id": alice_id, "amount": 10.0},
                {"user_id": str(uuid.uuid4()), "amount": 10.0},
            ],
        },
    )
    assert non_member.status_code == 400, non_member.get_json()
    assert "active group member" in non_member.get_json()["error"]["message"].lower()


def test_payer_is_credited_even_when_not_in_the_split(group_of_two):
    api, alice_id, _, bob_id, group_id = group_of_two
    response = api.post(
        "/api/v1/expenses",
        json={
            "description": "Alice treats Bob",
            "amount": 40.0,
            "group_id": group_id,
            "paid_by": alice_id,
            "split_type": "exact",
            "splits": [{"user_id": bob_id, "amount": 40.0}],
        },
    )
    assert response.status_code == 201, response.get_json()

    balances = api.get(
        "/api/v1/expenses/settlements/group/%s/balances" % group_id,
    )
    assert balances.status_code == 200, balances.get_json()
    by_user = {
        str(balance["user_id"]): float(balance["balance"])
        for balance in payload(balances)["balances"]
    }
    assert by_user[str(alice_id)] == pytest.approx(40.0)
    assert by_user[str(bob_id)] == pytest.approx(-40.0)
    assert sum(by_user.values()) == pytest.approx(0.0)


def test_edit_without_splits_preserves_exact_ledger(group_of_two):
    api, alice_id, _, bob_id, group_id = group_of_two
    created = _create_exact(api, group_id, alice_id, alice_id, bob_id)
    original_splits = _split_map(created)

    updated = api.put(
        "/api/v1/expenses/%s" % created["id"],
        json={"description": "Dinner after the museum"},
    )
    assert updated.status_code == 200, updated.get_json()
    expense = payload(updated)["expense"]
    assert expense["split_type"] == "exact"
    assert _split_map(expense) == original_splits


def test_editing_non_equal_amount_requires_new_splits(group_of_two):
    api, alice_id, _, bob_id, group_id = group_of_two
    created = _create_exact(api, group_id, alice_id, alice_id, bob_id)
    response = api.put(
        "/api/v1/expenses/%s" % created["id"],
        json={"amount": 120.0},
    )
    assert response.status_code == 400, response.get_json()
    assert "splits are required" in response.get_json()["error"]["message"].lower()


def test_percentage_rounding_reconciles_the_final_cent(group_of_two):
    api, alice_id, _, bob_id, group_id = group_of_two
    response = api.post(
        "/api/v1/expenses",
        json={
            "description": "Rounded percentage",
            "amount": 10.0,
            "group_id": group_id,
            "split_type": "percentage",
            "splits": [
                {"user_id": alice_id, "percentage": 33.33},
                {"user_id": bob_id, "percentage": 66.67},
            ],
        },
    )
    assert response.status_code == 201, response.get_json()
    expense = payload(response)["expense"]
    assert sum(_split_map(expense).values()) == pytest.approx(10.0)


def test_personal_expense_uses_owner_as_payer_and_updates_its_split(alice, bob):
    api, alice_id, _ = alice
    _, bob_id, _ = bob
    created = api.post(
        "/api/v1/expenses",
        json={
            "description": "Train ticket",
            "amount": 8.0,
            "paid_by": bob_id,
            "split_type": "none",
        },
    )
    assert created.status_code == 201, created.get_json()
    expense = payload(created)["expense"]
    assert str(expense["paid_by"]) == str(alice_id)

    updated = api.put(
        "/api/v1/expenses/%s" % expense["id"], json={"amount": 12.5},
    )
    assert updated.status_code == 200, updated.get_json()
    updated_expense = payload(updated)["expense"]
    assert _split_map(updated_expense) == {str(alice_id): 12.5}


def test_settlement_requires_a_party_and_cannot_exceed_debt(group_of_two, make_user):
    alice_api, alice_id, bob_api, bob_id, group_id = group_of_two
    carol_api, carol_id, carol_email = make_user("carol")
    added = alice_api.post(
        "/api/v1/expenses/groups/%s/members" % group_id,
        json={"email": carol_email},
    )
    assert added.status_code in (200, 201), added.get_json()

    expense = alice_api.post(
        "/api/v1/expenses",
        json={
            "description": "Museum tickets",
            "amount": 60.0,
            "group_id": group_id,
            "split_type": "equal",
            # Keep Carol outside this expense, despite her membership.
            "splits": [{"user_id": alice_id}, {"user_id": bob_id}],
        },
    )
    assert expense.status_code == 201, expense.get_json()

    # A third member cannot record a payment between Alice and Bob.
    not_a_party = carol_api.post(
        "/api/v1/expenses/settlements",
        json={
            "group_id": group_id,
            "from_user_id": bob_id,
            "to_user_id": alice_id,
            "amount": 10.0,
        },
    )
    assert not_a_party.status_code == 403, not_a_party.get_json()

    too_large = bob_api.post(
        "/api/v1/expenses/settlements",
        json={
            "group_id": group_id,
            "from_user_id": bob_id,
            "to_user_id": alice_id,
            "amount": 30.01,
        },
    )
    assert too_large.status_code == 400, too_large.get_json()
    assert "cannot exceed" in too_large.get_json()["error"]["message"].lower()

    recorded = bob_api.post(
        "/api/v1/expenses/settlements",
        json={
            "group_id": group_id,
            "from_user_id": bob_id,
            "to_user_id": alice_id,
            "amount": 30.0,
        },
    )
    assert recorded.status_code == 201, recorded.get_json()
    settlement_id = payload(recorded)["settlement"]["id"]
    unauthorized_delete = carol_api.delete(
        "/api/v1/expenses/settlements/%s" % settlement_id,
    )
    assert unauthorized_delete.status_code == 403, unauthorized_delete.get_json()

    with get_db() as session:
        still_active = session.get(Settlement, settlement_id)
        assert still_active is not None
        assert not still_active.is_deleted

    deleted = bob_api.delete("/api/v1/expenses/settlements/%s" % settlement_id)
    assert deleted.status_code == 200, deleted.get_json()
    deleted_data = payload(deleted)
    assert {
        str(row['user_id']): row['balance'] for row in deleted_data['balances']
    } == {alice_id: 30.0, bob_id: -30.0, carol_id: 0.0}
    assert deleted_data['debts']

    with get_db() as session:
        settlement = session.get(Settlement, settlement_id)
        assert settlement is not None
        assert settlement.is_deleted
        assert str(settlement.deleted_by) == str(bob_id)
        assert settlement.deleted_at is not None


def test_uuid_payer_can_be_another_member(group_of_two):
    api, alice_id, _, bob_id, group_id = group_of_two
    expense = _create_exact(api, group_id, bob_id, alice_id, bob_id)
    assert str(expense['paid_by']) == bob_id
    response = api.get('/api/v1/expenses/settlements/group/%s/balances' % group_id)
    balances = {str(row['user_id']): row['balance'] for row in payload(response)['balances']}
    assert balances == {alice_id: -25.0, bob_id: 25.0}


def test_legacy_group_without_balance_rows_can_credit_and_debit_payer(group_of_two):
    api, alice_id, _, bob_id, group_id = group_of_two
    with get_db() as session:
        session.query(GroupBalance).filter_by(group_id=group_id).delete()
    expense = _create_exact(api, group_id, alice_id, alice_id, bob_id)
    assert sum(_split_map(expense).values()) == pytest.approx(100.0)
    balances = api.get('/api/v1/expenses/settlements/group/%s/balances' % group_id)
    assert {str(row['user_id']): row['balance'] for row in payload(balances)['balances']} == {
        alice_id: 75.0, bob_id: -75.0,
    }


@pytest.mark.parametrize('split_type, field, weights', [
    ('equal', None, [1, 1, 1, 1]),
    ('percentage', 'percentage', [1, 33, 33, 33]),
    ('shares', 'shares', [1, 33, 33, 33]),
])
def test_small_totals_never_create_negative_splits(group_of_two, make_user, split_type, field, weights):
    api, alice_id, _, bob_id, group_id = group_of_two
    users = [alice_id, bob_id]
    for label in ('carol', 'dave'):
        _, uid, email = make_user(label)
        added = api.post('/api/v1/expenses/groups/%s/members' % group_id, json={'email': email})
        assert added.status_code in (200, 201), added.get_json()
        users.append(uid)
    entries = [{'user_id': uid, **({field: weight} if field else {})}
               for uid, weight in zip(users, weights)]
    response = api.post('/api/v1/expenses', json={
        'description': 'Two cents among four', 'group_id': group_id,
        'amount': 0.02, 'split_type': split_type, 'splits': entries,
    })
    assert response.status_code == 201, response.get_json()
    amounts = list(_split_map(payload(response)['expense']).values())
    assert all(amount >= 0 for amount in amounts)
    assert sum(amounts) == pytest.approx(0.02)


@pytest.mark.parametrize('split_type, field, weights', [
    ('percentage', 'percentage', [25, 75]),
    ('shares', 'shares', [1, 3]),
])
def test_metadata_edit_preserves_weighted_split_contract(group_of_two, split_type, field, weights):
    api, alice_id, _, bob_id, group_id = group_of_two
    created = api.post('/api/v1/expenses', json={
        'description': 'Weighted dinner', 'group_id': group_id, 'amount': 100,
        'split_type': split_type.upper(),
        'splits': [{'user_id': uid, field: weight} for uid, weight in zip([alice_id, bob_id], weights)],
    })
    assert created.status_code == 201, created.get_json()
    expense = payload(created)['expense']
    edited = api.put('/api/v1/expenses/%s' % expense['id'], json={'description': 'Edited dinner'})
    assert edited.status_code == 200, edited.get_json()
    updated = payload(edited)['expense']
    assert updated['split_type'] == split_type
    assert _split_map(updated) == _split_map(expense)


def test_invalid_percentages_leave_the_ledger_unchanged(group_of_two):
    api, alice_id, _, bob_id, group_id = group_of_two
    created = _create_exact(api, group_id, alice_id, alice_id, bob_id)
    rejected = api.put('/api/v1/expenses/%s' % created['id'], json={
        'split_type': 'percentage',
        'splits': [{'user_id': alice_id, 'percentage': 20}, {'user_id': bob_id, 'percentage': 50}],
    })
    assert rejected.status_code == 400, rejected.get_json()
    fetched = api.get('/api/v1/expenses/%s' % created['id'])
    assert _split_map(payload(fetched)['expense']) == _split_map(created)
    balances = api.get('/api/v1/expenses/settlements/group/%s/balances' % group_id)
    assert {str(row['user_id']): row['balance'] for row in payload(balances)['balances']} == {
        alice_id: 75.0, bob_id: -75.0,
    }
