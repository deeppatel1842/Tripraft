# Purpose: Idempotency middleware. Stores the result of a mutating request keyed by its `Idempotency-Key`.
"""
Idempotency middleware.

Stores the result of a mutating request keyed by its `Idempotency-Key`
header, so a client that retries after a dropped response gets the original
result instead of executing the operation twice.

Three properties matter here and none of them held before:

* **Scope.** The cache key mixes in the caller, the method and the path. The
  previous key was the bare header value, so any user replaying any key got
  back whoever's response happened to be stored under it, and their own
  request never ran (audit P0-13).
* **Atomic reservation.** The key is claimed with SET NX before the handler
  runs. Two concurrent retries previously both passed the "is it cached?"
  check and both executed -- a double charge (audit P1-15).
* **2xx only.** A 404 or a 403 is a fact about right now, not a result worth
  replaying for a day (audit P1-15).

Keys are bounded in length and charset, and the stored key is a digest, so a
caller cannot grow Redis without limit (audit P2-27).
"""

import hashlib
import json
import logging
import re

from flask import g, make_response, request

logger = logging.getLogger(__name__)

# How long a completed result stays replayable.
_RESULT_TTL = 86400  # 24 hours

# How long a reservation survives if the worker dies mid-request. Short, so a
# crash cannot lock a key out for the full result TTL.
_INFLIGHT_TTL = 90  # seconds

_MUTATING_METHODS = frozenset(('POST', 'PUT', 'PATCH', 'DELETE'))

# Deliberately strict: printable, bounded, and no characters that would let a
# caller smuggle structure into the Redis key namespace.
_KEY_PATTERN = re.compile(r'^[A-Za-z0-9._:\-]{8,200}$')

_INFLIGHT_MARKER = '__in_flight__'


def _caller_scope():
    """A stable identity for the caller, resolved without the auth decorators.

    Idempotency runs in before_request, which is earlier than the route's
    @require_auth, so g.user_id is not populated yet. The access token is
    decoded directly to recover the subject. Requests with no usable token
    fall back to the peer address: still scoped, so no cross-caller replay is
    possible either way.
    """
    try:
        from app.auth.security.decorators import get_access_token
        from app.auth.security.jwt import decode_token

        token = get_access_token()
        if token:
            payload = decode_token(token)
            if payload and payload.get('type') == 'access' and payload.get('sub'):
                return 'u:%s' % payload['sub']
    except Exception:  # pragma: no cover - identity is best effort
        logger.debug('Idempotency: could not resolve caller from token', exc_info=True)
    return 'a:%s' % (request.remote_addr or '-')


def _cache_key(key):
    """Digest of caller + method + path + client key.

    Hashed rather than concatenated so the Redis key is a fixed size
    regardless of how long the path or the client's key is.
    """
    material = '\x00'.join((_caller_scope(), request.method, request.path, key))
    return 'idempotency:%s' % hashlib.sha256(material.encode('utf-8')).hexdigest()


def _replay(stored):
    """Rebuild a response from a stored payload, or None if unusable."""
    try:
        data = json.loads(stored)
        response = make_response(data['body'], data['status'])
        response.headers['Content-Type'] = data.get(
            'content_type', 'application/json'
        )
        response.headers['X-Idempotent-Replay'] = 'true'
        return response
    except Exception:
        logger.warning('Idempotency: discarding unreadable cache entry')
        return None


def init_idempotency(app):
    """Register the request hooks that implement idempotent replay."""

    @app.before_request
    def check_idempotency_key():
        if request.method not in _MUTATING_METHODS:
            return None

        key = request.headers.get('Idempotency-Key')
        if not key:
            return None

        if not _KEY_PATTERN.match(key):
            return make_response(
                json.dumps({
                    'success': False,
                    'error': {
                        'code': 'INVALID_IDEMPOTENCY_KEY',
                        'message': (
                            'Idempotency-Key must be 8-200 characters of '
                            'letters, digits, dot, underscore, colon or hyphen.'
                        ),
                    },
                }),
                400,
                {'Content-Type': 'application/json'},
            )

        redis = app.extensions.get('redis')
        if not redis:
            return None

        cache_key = _cache_key(key)

        # Claim the key before doing any work. The winner of this SET NX is
        # the only request that executes; everyone else either replays the
        # stored result or is told the original is still running.
        try:
            reserved = redis.set(
                cache_key, _INFLIGHT_MARKER, nx=True, ex=_INFLIGHT_TTL
            )
        except Exception:
            # Redis is the whole mechanism; without it, fall through and let
            # the request execute normally rather than failing the call.
            logger.warning('Idempotency: reservation failed, proceeding unguarded')
            return None

        if reserved:
            g._idempotency_key = cache_key
            return None

        try:
            stored = redis.get(cache_key)
        except Exception:
            return None

        if stored is None:
            # The reservation expired between SET NX and GET. Claim it once
            # more before executing; treating it as ours without another
            # atomic claim reintroduced the double-execution race.
            try:
                reclaimed = redis.set(
                    cache_key, _INFLIGHT_MARKER, nx=True, ex=_INFLIGHT_TTL
                )
            except Exception:
                logger.warning('Idempotency: reservation reclaim failed')
                return None
            if reclaimed:
                g._idempotency_key = cache_key
                return None
            return make_response(
                json.dumps({
                    'success': False,
                    'error': {
                        'code': 'IDEMPOTENT_REQUEST_IN_PROGRESS',
                        'message': 'A request with this Idempotency-Key is still being processed. Retry shortly.',
                    },
                }),
                409,
                {'Content-Type': 'application/json'},
            )

        if isinstance(stored, bytes):
            stored = stored.decode('utf-8', 'replace')

        if stored == _INFLIGHT_MARKER:
            return make_response(
                json.dumps({
                    'success': False,
                    'error': {
                        'code': 'IDEMPOTENT_REQUEST_IN_PROGRESS',
                        'message': (
                            'A request with this Idempotency-Key is still '
                            'being processed. Retry shortly.'
                        ),
                    },
                }),
                409,
                {'Content-Type': 'application/json'},
            )

        return _replay(stored) or None

    @app.after_request
    def store_idempotency_result(response):
        cache_key = getattr(g, '_idempotency_key', None)
        if not cache_key:
            return response

        redis = app.extensions.get('redis')
        if not redis:
            return response

        # Only a success is worth replaying. Anything else releases the
        # reservation so the caller can legitimately retry.
        if not (200 <= response.status_code < 300) or response.direct_passthrough:
            try:
                redis.delete(cache_key)
            except Exception:
                pass
            g._idempotency_key = None
            return response

        try:
            payload = json.dumps({
                'status': response.status_code,
                'body': response.get_data(as_text=True),
                'content_type': response.headers.get(
                    'Content-Type', 'application/json'
                ),
            })
            redis.set(cache_key, payload, ex=_RESULT_TTL)
        except Exception:
            # Could not store the result: drop the reservation rather than
            # leave a key that replays nothing.
            try:
                redis.delete(cache_key)
            except Exception:
                pass

        g._idempotency_key = None
        return response

    @app.teardown_request
    def release_idempotency_reservation(exc):
        # after_request is skipped when the request dies with an unhandled
        # exception; without this the key would stay claimed until the
        # in-flight TTL expired.
        if exc is None:
            return
        cache_key = getattr(g, '_idempotency_key', None)
        if not cache_key:
            return
        redis = app.extensions.get('redis')
        if not redis:
            return
        try:
            redis.delete(cache_key)
        except Exception:
            pass
