# Purpose: Regression tests for p3 contracts, including success and failure behavior.
"""Behavioral verification for the remaining Appendix A P3 contracts."""
from app.core.config import Config
from app.trips.models import GroupActivity, Notification
from uuid import uuid4


def test_deprecated_alias_rejects_an_unsupported_successor_method(alice):
    api, _, _ = alice
    response = api.delete('/api/v2/group-planner/health')
    assert response.status_code == 405
    assert 'Location' not in response.headers


def test_deprecated_get_retains_query_and_publishes_deprecation_headers(client):
    response = client.get('/api/v2/group-planner/health?probe=1')
    assert response.status_code == 308
    assert response.headers['Location'].endswith('/api/v1/group-planner/health?probe=1')
    assert response.headers['Deprecation'] == 'true'
    assert response.headers['Sunset'] == Config.API_SUNSET_DATE


def test_health_endpoints_share_the_configured_application_version(client):
    versions = []
    for path in ['/api/health/live', '/api/v1/group-planner/health']:
        response = client.get(path)
        assert response.status_code == 200
        body = response.get_json()
        versions.append((body.get('data') or body)['version'])
    assert versions == [Config.APP_VERSION, Config.APP_VERSION]


def test_uuid_activity_and_notification_payloads_are_normalized_before_persistence():
    identifier = uuid4()
    payload = {'id': identifier, 'nested': [{'user_id': identifier}]}
    expected = {'id': str(identifier), 'nested': [{'user_id': str(identifier)}]}
    assert GroupActivity(details=payload).details == expected
    assert Notification(data=payload).data == expected
    assert payload['id'] is identifier
