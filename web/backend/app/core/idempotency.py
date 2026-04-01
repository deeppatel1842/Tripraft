"""
Idempotency middleware.
Stores request results keyed by `Idempotency-Key` header in Redis.
On duplicate POST/PUT with the same key, returns the cached response
instead of re-executing the handler.
"""

import json
import logging

from flask import g, request

logger = logging.getLogger(__name__)

_IDEMPOTENCY_TTL = 86400  # 24 hours


def init_idempotency(app):
    """Register before/after request hooks for idempotency."""

    @app.before_request
    def check_idempotency_key():
        if request.method not in ('POST', 'PUT'):
            return None

        key = request.headers.get('Idempotency-Key')
        if not key:
            return None

        redis = app.extensions.get('redis')
        if not redis:
            return None

        cache_key = f"idempotency:{key}"
        try:
            cached = redis.get(cache_key)
        except Exception:
            return None

        if cached:
            try:
                data = json.loads(cached)
                from flask import make_response
                resp = make_response(data['body'], data['status'])
                resp.headers['Content-Type'] = 'application/json'
                resp.headers['X-Idempotent-Replay'] = 'true'
                return resp
            except Exception:
                return None

        # Mark that we're handling this key
        g._idempotency_key = cache_key

    @app.after_request
    def store_idempotency_result(response):
        cache_key = getattr(g, '_idempotency_key', None)
        if not cache_key:
            return response

        redis = app.extensions.get('redis')
        if not redis:
            return response

        # Only cache successful responses
        if response.status_code >= 500:
            return response

        try:
            payload = json.dumps({
                'status': response.status_code,
                'body': response.get_data(as_text=True),
            })
            redis.set(cache_key, payload, ex=_IDEMPOTENCY_TTL)
        except Exception:
            pass

        return response
