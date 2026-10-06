# Purpose: Regression tests for uuid ids, including success and failure behavior.
"""Step 1 — the integer -> UUIDv7 migration.

Every test here fails on the pre-fix code with a 422, a 400 or a 500. They are
the regression net for the defect class the audit called the single largest in
the backend: schemas and route helpers still treating UUID ids as integers.
"""
import uuid

import pytest
from conftest import error_of, payload

from app.core.schemas.fields import UUIDString
from marshmallow import Schema, ValidationError


# ---------------------------------------------------------------------------
# The shared field
# ---------------------------------------------------------------------------

class _IdSchema(Schema):
    id = UUIDString(required=True)


@pytest.mark.parametrize(
    "supplied",
    [
        "01923456-789a-7bcd-8ef0-123456789abc",
        "01923456-789A-7BCD-8EF0-123456789ABC",
        "{01923456-789a-7bcd-8ef0-123456789abc}",
        "urn:uuid:01923456-789a-7bcd-8ef0-123456789abc",
        "0192345678 9a7bcd8ef0123456789abc".replace(" ", ""),
    ],
)
def test_uuid_field_accepts_every_standard_spelling(supplied):
    loaded = _IdSchema().load({"id": supplied})["id"]
    assert isinstance(loaded, uuid.UUID)
    assert loaded == uuid.UUID("01923456-789a-7bcd-8ef0-123456789abc")


def test_uuid_field_deserialises_to_uuid_not_str():
    """The service layer compares against ORM columns, which are uuid.UUID.

    Returning a string here would make `expense.created_by == user_id`
    silently false -- the same mixed-type defect this migration removes.
    """
    loaded = _IdSchema().load({"id": "01923456-789a-7bcd-8ef0-123456789abc"})["id"]
    assert type(loaded) is uuid.UUID


@pytest.mark.parametrize("supplied", [1, "1", "42", "", "not-a-uuid", [], {}, 3.5])
def test_uuid_field_rejects_non_uuids(supplied):
    with pytest.raises(ValidationError):
        _IdSchema().load({"id": supplied})


def test_uuid_field_rejects_integers_rather_than_coercing():
    """An integer id is a caller still on the pre-UUID contract."""
    with pytest.raises(ValidationError) as excinfo:
        _IdSchema().load({"id": 7})
    assert "Not a valid UUID." in excinfo.value.messages["id"]


# ---------------------------------------------------------------------------
# P0-3 / P0-7 — expenses
# ---------------------------------------------------------------------------

def test_group_expense_can_be_created(group_of_two):
    """P0-3: group_id was fields.Integer, so this always returned 422."""
    alice_api, _, _, _, group_id = group_of_two
    response = alice_api.post(
        "/api/v1/expenses",
        json={
            "description": "Dinner",
            "amount": 90.0,
            "group_id": group_id,
            "split_type": "equal",
        },
    )
    assert response.status_code in (200, 201), response.get_json()
    assert payload(response)["expense"]["id"]


def test_expense_update_accepts_uuid_paid_by(group_of_two):
    """P0-7: the route did int(data['paid_by']) -> ValueError -> 500."""
    alice_api, alice_id, _, _, group_id = group_of_two
    created = alice_api.post(
        "/api/v1/expenses",
        json={
            "description": "Taxi",
            "amount": 40.0,
            "group_id": group_id,
            "split_type": "equal",
        },
    )
    expense_id = payload(created)["expense"]["id"]

    response = alice_api.put(
        "/api/v1/expenses/%s" % expense_id,
        json={"description": "Taxi to airport", "amount": 40.0, "paid_by": alice_id},
    )
    assert response.status_code == 200, response.get_json()


def test_expense_payer_can_be_another_member(group_of_two):
    """The create route used to overwrite any UUID payer with the caller.

    "Pay for someone else" is the whole point of a group expense.
    """
    alice_api, _, _, bob_id, group_id = group_of_two
    response = alice_api.post(
        "/api/v1/expenses",
        json={
            "description": "Hotel",
            "amount": 200.0,
            "group_id": group_id,
            "split_type": "equal",
            "paid_by": bob_id,
        },
    )
    assert response.status_code in (200, 201), response.get_json()
    assert str(payload(response)["expense"]["paid_by"]) == str(bob_id)


def test_expense_rejects_integer_group_id(alice):
    api, _, _ = alice
    response = api.post(
        "/api/v1/expenses",
        json={"description": "x", "amount": 1.0, "group_id": 1, "split_type": "equal"},
    )
    assert response.status_code in (400, 422)


# ---------------------------------------------------------------------------
# P0-2 / P0-6 — settlements
# ---------------------------------------------------------------------------

def test_settlement_can_be_created(group_of_two):
    """P0-2: group_id/from_user_id/to_user_id were all fields.Integer."""
    alice_api, alice_id, _, bob_id, group_id = group_of_two
    alice_api.post(
        "/api/v1/expenses",
        json={
            "description": "Brunch",
            "amount": 60.0,
            "group_id": group_id,
            "split_type": "equal",
        },
    )
    response = alice_api.post(
        "/api/v1/expenses/settlements",
        json={
            "group_id": group_id,
            "from_user_id": bob_id,
            "to_user_id": alice_id,
            "amount": 10.0,
        },
    )
    assert response.status_code in (200, 201), response.get_json()


@pytest.mark.parametrize(
    "suffix", ["", "/balances", "/simplified"]
)
def test_settlement_group_reads_resolve_the_group(group_of_two, suffix):
    """P0-6: parse_id() int()'d the UUID and returned None, so all three
    of these ran with group_id=None."""
    alice_api, _, _, _, group_id = group_of_two
    response = alice_api.get(
        "/api/v1/expenses/settlements/group/%s%s" % (group_id, suffix)
    )
    assert response.status_code == 200, response.get_json()


def test_settlement_group_read_rejects_malformed_id(alice):
    api, _, _ = alice
    response = api.get("/api/v1/expenses/settlements/group/not-a-uuid/balances")
    assert response.status_code == 400


def test_settlement_delete_returns_group_id(group_of_two):
    """P0-6: delete returned only a message, so the post-delete balance
    refresh in the route ran against group_id=None."""
    alice_api, alice_id, _, bob_id, group_id = group_of_two
    alice_api.post(
        "/api/v1/expenses",
        json={
            "description": "Museum",
            "amount": 50.0,
            "group_id": group_id,
            "split_type": "equal",
        },
    )
    created = alice_api.post(
        "/api/v1/expenses/settlements",
        json={
            "group_id": group_id,
            "from_user_id": bob_id,
            "to_user_id": alice_id,
            "amount": 5.0,
        },
    )
    settlement = payload(created).get("settlement") or {}
    settlement_id = settlement.get("id")
    assert settlement_id, created.get_json()

    response = alice_api.delete("/api/v1/expenses/settlements/%s" % settlement_id)
    assert response.status_code == 200, response.get_json()
    # The route can only refresh balances if the service handed back a group.
    assert "balances" in payload(response)


# ---------------------------------------------------------------------------
# P0-4 / P0-5 — invitations
# ---------------------------------------------------------------------------

def test_expense_invitation_can_be_created(expense_group):
    """P0-4: group_id was fields.Integer -> always 422."""
    api, _, group_id = expense_group
    response = api.post(
        "/api/v1/expenses/invitations",
        json={
            "group_id": group_id,
            "invitee_email": "invitee_%s@example.test" % uuid.uuid4().hex[:8],
        },
    )
    assert response.status_code in (200, 201), response.get_json()


# ---------------------------------------------------------------------------
# P0-8 — the users namespace
# ---------------------------------------------------------------------------

def test_users_me_reads_the_authenticated_user(alice):
    """P0-8: the route read g.current_user_id, which no decorator sets, so
    the service was handed None."""
    api, _, email = alice
    response = api.get("/api/v1/users/me")
    assert response.status_code == 200, response.get_json()
    user = payload(response).get("user") or payload(response)
    assert user.get("email") == email


def test_users_me_can_be_updated(alice):
    api, _, _ = alice
    response = api.patch(
        "/api/v1/users/me", json={"display_name": "Alice Renamed"}
    )
    assert response.status_code == 200, response.get_json()
    user = payload(response).get("user") or payload(response)
    assert user.get("display_name") == "Alice Renamed"
