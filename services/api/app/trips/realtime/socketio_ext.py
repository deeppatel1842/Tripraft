# Purpose: Flask-SocketIO extension singleton. Import `socketio` from here anywhere in the backend to emit events.
"""
Flask-SocketIO extension singleton.
Import `socketio` from here anywhere in the backend to emit events.
"""

import logging

from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

socketio = SocketIO()


def init_socketio(app):
    """Attach SocketIO to the Flask app. Call once from factory."""
    from app.core.config import get_config
    config = get_config()

    cors_origins = config.CORS_ORIGINS if hasattr(config, "CORS_ORIGINS") and config.CORS_ORIGINS else []

    kwargs = {
        "cors_allowed_origins": cors_origins,
        "async_mode": "gevent",
        "logger": False,
        "engineio_logger": False,
        "ping_timeout": config.SOCKETIO_PING_TIMEOUT,
        "ping_interval": config.SOCKETIO_PING_INTERVAL,
        "max_http_buffer_size": config.SOCKETIO_MAX_HTTP_BUFFER_SIZE,
    }

    # Use Redis as message queue for cross-pod event delivery
    redis_url = getattr(config, "REDIS_URL", None)
    if redis_url:
        kwargs["message_queue"] = redis_url

    socketio.init_app(app, **kwargs)
    logger.info("SocketIO initialized (async_mode=%s)", socketio.async_mode)
    return socketio
