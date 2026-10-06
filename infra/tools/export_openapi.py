# Purpose: Exports registered Flask paths and explicit admin schemas using a migrated disposable database.
"""Export registered Flask routes without opening or modifying the user's database.

Known operations have explicit response schemas. Other response payloads remain
unknown until their contracts are specified; route discovery is not schema inference.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / 'services/api'
sys.path.insert(0, str(API))


def ref(name):
    return {'$ref': f'#/components/schemas/{name}'}


def response(schema):
    return {'description': 'Response', 'content': {'application/json': {'schema': schema}}}


def envelope(data):
    return {'type': 'object', 'required': ['success', 'data'], 'properties': {
        'success': {'type': 'boolean'}, 'data': data, 'message': {'type': 'string'},
    }}


def build(application):
    schemas = {
        'User': {'type': 'object', 'required': ['id', 'email', 'is_admin'], 'properties': {
            'id': {'type': 'string', 'format': 'uuid'}, 'email': {'type': 'string'},
            'display_name': {'type': ['string', 'null']}, 'is_admin': {'type': 'boolean'},
        }},
        'Health': {'type': 'object', 'required': ['status', 'timestamp'], 'properties': {
            'status': {'type': 'string'}, 'timestamp': {'type': 'string'},
            'service': {'type': 'string'}, 'version': {'type': 'string'},
            'checks': {'type': 'object', 'additionalProperties': {'type': 'object', 'required': ['status'], 'properties': {
                'status': {'type': 'string'}, 'note': {'type': 'string'}, 'error': {'type': 'string'},
            }}},
        }},
        'AuditRecord': {'type': 'object', 'properties': {
            'id': {'type': ['integer', 'string']}, 'created_at': {'type': 'string'},
            'entity_type': {'type': 'string'}, 'action': {'type': 'string'}, 'ingested_by': {'type': ['string', 'null']},
        }},
        'AuditData': {'type': 'object', 'required': ['total', 'logs'], 'properties': {
            'total': {'type': 'integer'}, 'logs': {'type': 'array', 'items': ref('AuditRecord')},
        }},
        'MeResponse': envelope({'type': 'object', 'required': ['user'], 'properties': {'user': ref('User')}}),
        'AuditResponse': envelope(ref('AuditData')),
    }
    paths = {}
    for rule in sorted(application.url_map.iter_rules(), key=lambda r: (r.rule, r.endpoint)):
        if not (rule.rule.startswith('/api/v1/') or rule.rule.startswith('/api/health/')):
            continue
        route = re.sub(r'<(?:[^:>]+:)?([^>]+)>', r'{\1}', rule.rule)
        for method in sorted(rule.methods - {'OPTIONS', 'HEAD'}):
            route_id = re.sub(r'[^a-zA-Z0-9]+', '_', route).strip('_')
            operation = {'operationId': rule.endpoint.replace('.', '_') + '_' + method.lower() + '_' + route_id,
                         'responses': {'default': response({})},
                         'description': 'Registered route. Response payload is unspecified unless an explicit schema is attached.'}
            if rule.arguments:
                operation['parameters'] = [{'name': name, 'in': 'path', 'required': True, 'schema': {
                    'type': 'integer' if rule._converters[name].__class__.__name__ == 'IntegerConverter' else 'string',
                }} for name in sorted(rule.arguments)]
            if route == '/api/v1/auth/me' and method == 'GET':
                operation['responses']['200'] = response(ref('MeResponse'))
                operation['security'] = [{'cookieAuth': []}]
            elif route in {'/api/health/live', '/api/health/ready', '/api/health/'}:
                operation['responses']['200'] = response(ref('Health'))
                if route.endswith('/ready'):
                    operation['responses']['503'] = response(ref('Health'))
            elif route == '/api/v1/admin/audit' and method == 'GET':
                operation['responses']['200'] = response(ref('AuditResponse'))
                operation['security'] = [{'cookieAuth': []}]
                operation['parameters'] = [
                    {'name': name, 'in': 'query', 'schema': {'type': 'integer', 'minimum': 0}}
                    for name in ('limit', 'offset')
                ]
            paths.setdefault(route, {})[method.lower()] = operation
    return {'openapi': '3.1.0', 'info': {'title': 'TripRaft API', 'version': '2.0.0',
            'description': 'Route inventory with explicit operations schemas for the admin client. Unspecified payloads remain unknown.'},
            'paths': paths, 'components': {'schemas': schemas,
            'securitySchemes': {'cookieAuth': {'type': 'apiKey', 'in': 'cookie', 'name': 'access_token'}}}}


if __name__ == '__main__':
    os.environ['FLASK_ENV'] = 'development'
    os.environ['SECRET_KEY'] = 'schema-export-disposable-development-secret'
    os.environ['REDIS_URL'] = ''
    scratch = ROOT / 'extra/build/schema-export'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='schema-', dir=scratch) as temp:
        os.environ['DATABASE_URL'] = 'sqlite:///' + (Path(temp) / 'schema.db').as_posix()
        from alembic import command
        from alembic.config import Config as AlembicConfig
        config = AlembicConfig(str(API / 'alembic.ini'))
        config.set_main_option('script_location', str(API / 'migrations'))
        command.upgrade(config, 'head')
        from app.core.factory import create_app
        spec = build(create_app())
        from app.core.db.connection import engine
        engine.dispose()
    target = API / 'openapi.json'
    target.write_text(json.dumps(spec, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(f'Exported {len(spec["paths"])} paths to {target}')
