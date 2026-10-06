# Purpose: Regression tests for group access controls, including success and failure behavior.
"""Phase 1 access-control and vault lifecycle regression coverage."""
import io
import os
import uuid

from werkzeug.datastructures import FileStorage

from conftest import payload
from app.trips.models import TravelGroup, TripMember, VaultDocument
from app.core.db.connection import get_db_session
from app.itinerary.services.export_service import ExportService
from app.trips.services.travel_group_service import GroupService
from app.trips.services.vault_service import VaultService


def _create_travel_group(api):
    response = api.post(
        '/api/v1/group-planner/groups',
        json={'name': 'Access %s' % uuid.uuid4().hex[:8]},
    )
    assert response.status_code in (200, 201), response.get_json()
    group = payload(response).get('group') or payload(response)
    return group['id']


def _add_trip_member(group_id, user_id, role='member'):
    with get_db_session() as session:
        session.add(TripMember(group_id=group_id, user_id=user_id, role=role, is_active=True))
        session.commit()


def test_exports_require_active_trip_membership(alice, bob):
    alice_api, _, _ = alice
    _, bob_id, _ = bob
    group_id = _create_travel_group(alice_api)

    ok, result = ExportService.generate_ical(group_id, bob_id)
    assert not ok
    assert result['error'] == 'Not a member of this group'


def test_vault_uses_signature_and_removes_bytes_on_delete(alice, monkeypatch, tmp_path):
    api, user_id, _ = alice
    group_id = _create_travel_group(api)
    monkeypatch.setenv('UPLOAD_DIR', str(tmp_path))
    uploaded = FileStorage(
        stream=io.BytesIO(b'%PDF-1.7\ntrusted content'),
        filename='misleading.jpg',
        content_type='text/plain',
    )

    ok, result = VaultService.upload_file(group_id, user_id, uploaded)
    assert ok, result
    document = result['document']
    assert document['mime_type'] == 'application/pdf'

    # Get the server filename from the row; the public response deliberately
    # exposes only the original name.
    with get_db_session() as session:
        stored = session.get(VaultDocument, document['id'])
        assert stored is not None
        path = VaultService._document_path(group_id, stored.filename)
    assert path.endswith('.pdf')
    assert os.path.isfile(path)

    deleted, delete_result = VaultService.delete_file(group_id, document['id'], user_id)
    assert deleted, delete_result
    assert not os.path.exists(path)


def test_vault_delete_requires_uploader_or_group_admin(alice, bob):
    alice_api, alice_id, _ = alice
    _, bob_id, _ = bob
    group_id = _create_travel_group(alice_api)
    _add_trip_member(group_id, bob_id)

    with get_db_session() as session:
        document = VaultDocument(
            group_id=group_id,
            filename='%s.pdf' % uuid.uuid4().hex,
            original_filename='private.pdf',
            mime_type='application/pdf',
            file_size=1,
            uploaded_by=alice_id,
        )
        session.add(document)
        session.commit()
        doc_id = str(document.id)

    ok, result = VaultService.delete_file(group_id, doc_id, bob_id)
    assert not ok
    assert result['status_code'] == 403


def test_expense_link_operations_require_travel_group_admin(alice, bob):
    alice_api, _, _ = alice
    _, bob_id, _ = bob
    group_id = _create_travel_group(alice_api)
    _add_trip_member(group_id, bob_id, role='member')

    ok, result = GroupService.link_expense_group(group_id, bob_id, str(uuid.uuid4()))
    assert not ok
    assert result['status_code'] == 403


def test_expense_summary_requires_membership_in_linked_expense_group(alice, bob):
    alice_api, alice_id, _ = alice
    _, bob_id, _ = bob
    travel_group_id = _create_travel_group(alice_api)
    _add_trip_member(travel_group_id, bob_id)

    expense = alice_api.post(
        '/api/v1/expenses/groups', json={'name': 'Private expenses'},
    )
    assert expense.status_code in (200, 201), expense.get_json()
    expense_group_id = (payload(expense).get('group') or payload(expense))['id']

    with get_db_session() as session:
        group = session.get(TravelGroup, travel_group_id)
        group.expense_group_id = expense_group_id
        session.commit()

    ok, result = GroupService.get_expense_summary(travel_group_id, bob_id)
    assert not ok
    assert result['status_code'] == 403
