"""
Health Check Endpoint
======================
Simple health and readiness checks.
"""
import logging
from datetime import datetime, timezone

from app.core.config import Config
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/', methods=['GET'])
@health_bp.route('/live', methods=['GET'])
def liveness():
    """Liveness probe — is the service running?"""
    return jsonify({
        'status': 'healthy',
        'service': Config.APP_NAME,
        'version': Config.APP_VERSION,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })


@health_bp.route('/ready', methods=['GET'])
def readiness():
    """Readiness probe — is the service ready to accept traffic?"""
    checks = {
        'database': _check_database(),
        'cache': _check_cache(),
    }
    
    all_healthy = all(c['status'] == 'healthy' for c in checks.values())
    status_code = 200 if all_healthy else 503
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'checks': checks,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }), status_code


def _check_database() -> dict:
    """Check database connectivity."""
    try:
        from app.infrastructure.db import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return {'status': 'healthy'}
    except Exception as e:
        logger.warning('Database health check failed: %s', e)
        return {'status': 'unhealthy', 'error': str(e)}


def _check_cache() -> dict:
    """Check Redis connectivity."""
    try:
        from app.infrastructure.cache import redis_client
        if redis_client.available:
            return {'status': 'healthy'}
        return {'status': 'unavailable', 'note': 'Cache disabled'}
    except Exception as e:
        return {'status': 'unavailable', 'error': str(e)}
