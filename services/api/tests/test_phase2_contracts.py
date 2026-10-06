# Purpose: Regression tests for phase2 contracts, including success and failure behavior.
"""Phase 2 regressions for API contracts, money, RBAC, and calendar exports."""
from datetime import date
from decimal import Decimal
import uuid

import pytest
from icalendar import Calendar

from conftest import payload
from app.core.apiutils.validators import parse_query_int
from app.itinerary.routes.trips import _apply_place_filters
from app.expenses.models import money_to_json
from app.trips.models import Place, TravelGroup, TripMember
from app.core.db.connection import get_db_session
from app.itinerary.services.export_service import ExportService
from app.expenses.services.expense_service import ExpenseServiceSQL, SplitValidationError
from app.itinerary.services.travel_place_service import PlaceService, PlaceValidationError


def _travel_group(api, *, name='P2 contracts'):
    response = api.post(
        '/api/v1/group-planner/groups',
        json={'name': '%s %s' % (name, uuid.uuid4().hex[:8])},
    )
    assert response.status_code in (200, 201), response.get_json()
    group = payload(response).get('group') or payload(response)
    return group['id']


def test_malformed_query_integer_is_a_400_and_bounds_are_clamped(app, client):
    malformed = client.get('/api/v1/places/autocomplete?q=Paris&limit=not-a-number')
    assert malformed.status_code == 400
    assert malformed.get_json()['error']['message'] == 'limit must be an integer'

    with app.test_request_context('/?limit=-4&offset=-9'):
        assert parse_query_int('limit', 20, minimum=1, maximum=100) == 1
        assert parse_query_int('offset', 0, minimum=0) == 0


def test_trip_options_bypasses_json_schema_validation(client):
    response = client.raw.open('/api/v1/trip-planner/generate', method='OPTIONS')
    assert response.status_code == 200


def test_trip_filters_exclude_require_and_prioritize_named_places():
    places = [
        {'id': 1, 'name': 'Museum', 'place_name': 'Museum', 'tags': ['indoor']},
        {'id': 2, 'name': 'Sunset Beach', 'place_name': 'Sunset Beach', 'tags': ['beach', 'viewpoint']},
        {'id': 3, 'name': 'City Park', 'place_name': 'City Park', 'tags': ['park']},
    ]
    filtered, missing = _apply_place_filters(
        places,
        excluded='museum',
        required='beach',
        requested_places='sunset beach',
    )
    assert missing == []
    assert [place['id'] for place in filtered] == [2]

    _, missing = _apply_place_filters(
        places,
        excluded=None,
        required=None,
        requested_places='not in this city',
    )
    assert missing == ['not in this city']


def test_money_input_is_decimal_and_share_rounding_reconciles_every_cent(group_of_two, make_user):
    api, alice_id, _, bob_id, group_id = group_of_two
    _, carol_id, carol_email = make_user('phase2-carol')
    added = api.post(
        '/api/v1/expenses/groups/%s/members' % group_id,
        json={'email': carol_email},
    )
    assert added.status_code in (200, 201), added.get_json()

    response = api.post(
        '/api/v1/expenses',
        json={
            'description': 'Three-way split',
            'amount': '10.00',
            'group_id': group_id,
            'paid_by': alice_id,
            'split_type': 'shares',
            'splits': [
                {'user_id': alice_id, 'shares': 1},
                {'user_id': bob_id, 'shares': 1},
                {'user_id': carol_id, 'shares': 1},
            ],
        },
    )
    assert response.status_code == 201, response.get_json()
    expense = payload(response)['expense']
    assert sum(Decimal(str(split['amount'])) for split in expense['splits']) == Decimal('10.00')
    assert money_to_json(Decimal('19.999')) == 20.0


def test_invalid_dates_are_rejected_without_substitution(alice):
    with pytest.raises(SplitValidationError, match='expense_date'):
        ExpenseServiceSQL._parse_expense_date('not-a-date')
    with pytest.raises(PlaceValidationError, match='visit_date'):
        PlaceService._parse_visit_date('not-a-date')

    api, _, _ = alice
    invalid_expense = api.post(
        '/api/v1/expenses',
        json={
            'description': 'Invalid date',
            'amount': '1.00',
            'expense_date': 'not-a-date',
        },
    )
    assert invalid_expense.status_code == 400, invalid_expense.get_json()

    group_id = _travel_group(api, name='Invalid date')
    invalid_place = api.post(
        '/api/v1/group-planner/groups/%s/places' % group_id,
        json={'name': 'Invalid date place', 'visit_date': 'not-a-date'},
    )
    assert invalid_place.status_code == 400, invalid_place.get_json()


def test_zero_coordinates_and_budget_are_serialized():
    group = TravelGroup(
        id=uuid.uuid4(),
        name='Equator',
        created_by=uuid.uuid4(),
        destination_lat=0.0,
        destination_lng=0.0,
        estimated_budget=Decimal('0.00'),
    )
    place = Place(
        id=uuid.uuid4(),
        group_id=group.id,
        name='Prime Meridian',
        added_by=group.created_by,
        latitude=0.0,
        longitude=0.0,
    )
    assert group.to_dict()['destination_coordinates'] == {'lat': 0.0, 'lng': 0.0}
    assert group.to_dict()['estimated_budget'] == 0.0
    assert place.to_dict()['coordinates'] == [0.0, 0.0]


def test_chat_delete_requires_active_membership_and_allows_group_admin(alice, bob):
    alice_api, alice_id, _ = alice
    bob_api, bob_id, _ = bob
    group_id = _travel_group(alice_api, name='Chat delete')
    sent = alice_api.post(
        '/api/v1/group-planner/groups/%s/messages' % group_id,
        json={'content': 'Private chat message'},
    )
    assert sent.status_code in (200, 201), sent.get_json()
    message_id = (payload(sent).get('message') or payload(sent))['id']

    denied = bob_api.delete('/api/v1/group-planner/messages/%s' % message_id)
    assert denied.status_code == 403, denied.get_json()

    with get_db_session() as session:
        session.add(TripMember(group_id=group_id, user_id=bob_id, role='admin', is_active=True))
        session.commit()

    deleted = bob_api.delete('/api/v1/group-planner/messages/%s' % message_id)
    assert deleted.status_code == 200, deleted.get_json()


def test_ical_all_day_events_have_exclusive_end_dates(alice):
    api, user_id, _ = alice
    group_id = _travel_group(api, name='Calendar')
    with get_db_session() as session:
        group = session.get(TravelGroup, group_id)
        group.start_date = date(2026, 6, 1)
        group.end_date = date(2026, 6, 3)
        session.add(Place(
            group_id=group_id,
            name='Museum',
            visit_date=date(2026, 6, 2),
            added_by=user_id,
        ))
        session.commit()

    ok, calendar_bytes = ExportService.generate_ical(group_id, user_id)
    assert ok, calendar_bytes
    events = [item for item in Calendar.from_ical(calendar_bytes).walk() if item.name == 'VEVENT']
    trip_event = next(
        event for event in events
        if str(event.decoded('summary')).startswith('Trip: Calendar')
    )
    place_event = next(
        event for event in events
        if str(event.decoded('summary')) == 'Visit: Museum'
    )
    assert trip_event.decoded('dtend') == date(2026, 6, 4)
    assert place_event.decoded('dtend') == date(2026, 6, 3)
