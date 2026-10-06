# Purpose: Socket.IO event handlers for Group Planner real-time collaboration. Rooms: one room per group, named "group:<group_id>".
"""
Socket.IO event handlers for Group Planner real-time collaboration.

Rooms: one room per group, named "group:<group_id>".
Events emitted TO clients:
  place:added, place:voted, poll:voted, checklist:toggled,
  itinerary:updated, member:joined, member:left, presence:update
Events received FROM clients:
  join_group, leave_group

Security:
  - JWT validated on connect (handshake auth.token)
  - Group membership verified on join_group
  - Presence stored in Redis (TTL-based cleanup) instead of in-memory dict
"""

import logging
from datetime import datetime, timezone

from app.trips.realtime.socketio_ext import socketio
from flask import request
from flask_socketio import disconnect, emit, join_room, leave_room

logger = logging.getLogger(__name__)

# Redis-backed presence (falls back to in-memory when Redis unavailable)
_PRESENCE_TTL = 300  # 5 minutes

# Redis is the production source of truth. The process-local fallback keeps
# development and single-worker deployments functional rather than silently
# dropping every presence event when Redis is temporarily unavailable.
_LOCAL_PRESENCE = {}
_LOCAL_SID_MAP = {}


def _get_redis():
    """Lazy import to avoid circular dependency."""
    try:
        from app.core.cache.redis import redis_client
        if redis_client.available:
            return redis_client._client
    except Exception:
        pass
    return None


def _presence_key(group_id: str) -> str:
    return f"ws:presence:{group_id}"


def _sid_map_key() -> str:
    return "ws:sid_map"


def _room_name(group_id: str) -> str:
    return f"group:{group_id}"


def _authenticate_socket(auth) -> dict | None:
    """Validate JWT from socket handshake or httpOnly cookie. Returns decoded payload or None."""
    token = None
    if auth and isinstance(auth, dict):
        token = auth.get("token")

    # Fallback: read httpOnly access_token cookie (browser cookie-mode auth)
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        return None
    try:
        from app.auth.security.jwt import decode_token, verify_token
        if not verify_token(token, token_type="access"):
            return None
        return decode_token(token)
    except Exception as exc:
        logger.warning("Socket JWT verification failed: %s", exc)
        return None


def _verify_group_membership(group_id: str, user_id: str) -> bool:
    """Check that user_id is an active member of group_id."""
    try:
        from app.trips.models import TripMember
        from app.core.db.connection import get_db_session
        with get_db_session() as session:
            member = session.query(TripMember).filter(
                TripMember.group_id == group_id,
                TripMember.user_id == user_id,
                TripMember.is_active == True,
            ).first()
            return member is not None
    except Exception as exc:
        logger.error("Membership check failed: %s", exc)
        return False


def _set_presence(group_id: str, user_id: str, sid: str, email: str):
    """Record one socket without hiding a user's other tabs/sockets."""
    r = _get_redis()
    now = datetime.now(timezone.utc).isoformat()
    if r:
        import json
        key = _presence_key(group_id)
        existing_raw = r.hget(key, str(user_id))
        try:
            existing = json.loads(existing_raw) if existing_raw else {}
        except (TypeError, ValueError):
            existing = {}
        sids = set(existing.get('sids', []))
        sids.add(sid)
        r.hset(key, str(user_id), json.dumps({
            'sids': sorted(sids),
            'email': email or existing.get('email', ''),
            'joined_at': existing.get('joined_at', now),
        }))
        r.hset(_sid_map_key(), sid, json.dumps({
            'group_id': str(group_id), 'user_id': str(user_id),
        }))
        r.expire(key, _PRESENCE_TTL)
        r.expire(_sid_map_key(), _PRESENCE_TTL)
        return

    members = _LOCAL_PRESENCE.setdefault(str(group_id), {})
    entry = members.setdefault(str(user_id), {
        'sids': set(), 'email': email, 'joined_at': now,
    })
    entry['sids'].add(sid)
    if email:
        entry['email'] = email
    _LOCAL_SID_MAP[sid] = {'group_id': str(group_id), 'user_id': str(user_id)}


def _remove_presence(group_id: str, user_id: str, sid: str):
    """Remove one socket; retain the user while another tab remains online."""
    r = _get_redis()
    if r:
        import json
        key = _presence_key(group_id)
        existing_raw = r.hget(key, str(user_id))
        try:
            existing = json.loads(existing_raw) if existing_raw else {}
        except (TypeError, ValueError):
            existing = {}
        sids = set(existing.get('sids', []))
        sids.discard(sid)
        if sids:
            existing['sids'] = sorted(sids)
            r.hset(key, str(user_id), json.dumps(existing))
        else:
            r.hdel(key, str(user_id))
        r.hdel(_sid_map_key(), sid)
        return

    members = _LOCAL_PRESENCE.get(str(group_id), {})
    entry = members.get(str(user_id))
    if entry:
        entry['sids'].discard(sid)
        if not entry['sids']:
            members.pop(str(user_id), None)
    _LOCAL_SID_MAP.pop(sid, None)


def _get_presence_list(group_id: str) -> list:
    """Return list of online users in a group from Redis."""
    r = _get_redis()
    if not r:
        return [
            {
                'user_id': user_id,
                'email': entry.get('email'),
                'joined_at': entry.get('joined_at'),
            }
            for user_id, entry in _LOCAL_PRESENCE.get(str(group_id), {}).items()
            if entry.get('sids')
        ]
    import json
    key = _presence_key(group_id)
    members = r.hgetall(key)
    result = []
    for uid_str, info_json in members.items():
        try:
            info = json.loads(info_json)
            result.append({
                "user_id": uid_str,
                "email": info.get("email"),
                "joined_at": info.get("joined_at"),
            })
        except (ValueError, TypeError):
            continue
    return result


def _refresh_presence(group_id: str, user_id: str, sid: str) -> bool:
    """Refresh the TTL for an already-authorized socket presence entry."""
    r = _get_redis()
    if not r:
        return sid in _LOCAL_SID_MAP
    import json
    mapping = r.hget(_sid_map_key(), sid)
    try:
        data = json.loads(mapping) if mapping else {}
    except (TypeError, ValueError):
        return False
    if data.get('group_id') != str(group_id) or data.get('user_id') != str(user_id):
        return False
    r.expire(_presence_key(group_id), _PRESENCE_TTL)
    r.expire(_sid_map_key(), _PRESENCE_TTL)
    return True


def _broadcast_presence(group_id: str):
    """Push current presence list to the group room."""
    online = _get_presence_list(group_id)
    socketio.emit(
        "presence:update",
        {"group_id": group_id, "online": online, "count": len(online)},
        room=_room_name(group_id),
    )


@socketio.on("connect")
def handle_connect(auth=None):
    payload = _authenticate_socket(auth)
    if not payload:
        logger.warning("WS connect rejected: invalid/missing JWT sid=%s", request.sid)
        disconnect()
        return False
    # Store user identity on the socket session for later use
    from flask import session as flask_session
    ws_user_id = payload.get("user_id") or payload.get("sub")
    if not ws_user_id:
        logger.warning("WS connect rejected: token carries no subject sid=%s", request.sid)
        disconnect()
        return False
    flask_session["ws_user_id"] = str(ws_user_id)
    flask_session["ws_email"] = payload.get("email", "")
    logger.debug("WS connect: sid=%s user=%s", request.sid, flask_session["ws_user_id"])


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    r = _get_redis()
    if r:
        import json
        mapping = r.hget(_sid_map_key(), sid)
        if mapping:
            try:
                data = json.loads(mapping)
                gid = data["group_id"]
                uid = data["user_id"]
                _remove_presence(gid, uid, sid)
                _broadcast_presence(gid)
            except (ValueError, KeyError):
                pass
    else:
        data = _LOCAL_SID_MAP.get(sid)
        if data:
            _remove_presence(data['group_id'], data['user_id'], sid)
            _broadcast_presence(data['group_id'])
    logger.debug("WS disconnect: sid=%s", sid)


@socketio.on("join_group")
def handle_join_group(data):
    """Client joins a group room.  Expects {group_id}."""
    group_id = data.get("group_id")
    if not group_id:
        return

    from flask import session as flask_session
    user_id = flask_session.get("ws_user_id")
    email = flask_session.get("ws_email", "")
    if not user_id:
        return

    # Verify membership
    if not _verify_group_membership(group_id, user_id):
        logger.warning("WS join_group denied: user %s not member of group %s", user_id, group_id)
        return

    room = _room_name(group_id)
    join_room(room)

    _set_presence(group_id, user_id, request.sid, email)
    _broadcast_presence(group_id)
    logger.debug("User %s joined room %s", user_id, room)


@socketio.on("leave_group")
def handle_leave_group(data):
    """Client leaves a group room.  Expects {group_id}."""
    group_id = data.get("group_id")
    if not group_id:
        return

    from flask import session as flask_session
    user_id = flask_session.get("ws_user_id")
    if not user_id:
        return

    room = _room_name(group_id)
    leave_room(room)

    _remove_presence(group_id, user_id, request.sid)
    _broadcast_presence(group_id)
    logger.debug("User %s left room %s", user_id, room)


@socketio.on('presence:heartbeat')
def handle_presence_heartbeat(data):
    """Keep an active, authorized socket visible beyond the presence TTL."""
    from flask import session as flask_session

    group_id = (data or {}).get('group_id')
    user_id = flask_session.get('ws_user_id')
    if not group_id or not user_id:
        return
    if not _verify_group_membership(group_id, user_id):
        return
    if _refresh_presence(group_id, user_id, request.sid):
        emit('presence:heartbeat_ack', {'group_id': group_id})


# ---- Helper used by services to broadcast to a group ----

def emit_to_group(group_id: int, event: str, payload: dict):
    """Emit an event to every client in a group room (fire-and-forget)."""
    try:
        socketio.emit(event, payload, room=_room_name(group_id))
    except Exception as exc:
        logger.warning("Failed to emit %s to group %s: %s", event, group_id, exc)


# ---- Chat Events ----

@socketio.on("chat:send")
def handle_chat_send(data):
    """Client sends a chat message via WebSocket."""
    from flask import session as flask_session
    user_id = flask_session.get("ws_user_id")
    if not user_id:
        return

    group_id = data.get("group_id")
    content = data.get("content", "").strip()
    if not group_id or not content:
        return

    if not _verify_group_membership(group_id, user_id):
        return

    try:
        from app.trips.services.chat_service import ChatService
        success, result = ChatService.send_message(
            group_id=group_id,
            sender_id=user_id,
            content=content[:5000],
            msg_type=data.get("type", "text"),
            metadata_json=data.get("metadata_json"),
            parent_message_id=data.get("parent_message_id"),
        )
        if success:
            emit("chat:message_ack", {"id": result.get("id")})
    except Exception as exc:
        logger.warning("chat:send failed: %s", exc)


@socketio.on("chat:typing")
def handle_chat_typing(data):
    """Broadcast typing indicator (no DB write)."""
    from flask import session as flask_session
    user_id = flask_session.get("ws_user_id")
    email = flask_session.get("ws_email", "")
    group_id = data.get("group_id")
    if not group_id or not user_id:
        return
    if not _verify_group_membership(group_id, user_id):
        logger.warning('WS typing denied: user %s not member of group %s', user_id, group_id)
        return

    socketio.emit(
        "chat:typing",
        {"user_id": user_id, "email": email, "group_id": group_id},
        room=_room_name(group_id),
        include_self=False,
    )


@socketio.on("chat:read")
def handle_chat_read(data):
    """Client marks messages as read."""
    from flask import session as flask_session
    user_id = flask_session.get("ws_user_id")
    group_id = data.get("group_id")
    message_id = data.get("message_id")
    if not group_id or not user_id or not message_id:
        return
    if not _verify_group_membership(group_id, user_id):
        return

    try:
        from app.trips.services.chat_service import ChatService
        ChatService.mark_read(group_id, user_id, message_id)
    except Exception as exc:
        logger.warning("chat:read failed: %s", exc)
