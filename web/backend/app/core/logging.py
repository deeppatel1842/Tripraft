"""
Logging Configuration
Extracted from the monolithic app.py for clean separation.
"""
import json as _json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production."""

    def format(self, record):
        log_entry = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'msg': record.getMessage(),
        }
        # Attach request correlation ID when running inside a Flask request
        try:
            from flask import g
            rid = getattr(g, 'request_id', None)
            if rid:
                log_entry['request_id'] = rid
        except RuntimeError:
            pass  # outside request context
        if record.exc_info and record.exc_info[0]:
            log_entry['exception'] = self.formatException(record.exc_info)
        return _json.dumps(log_entry, default=str)


def setup_logging(app):
    """
    Configure application logging.

    In production (FLASK_ENV != 'development'), logs are emitted as
    single-line JSON for easy ingestion by log aggregators.  In
    development the human-readable format from config is used.

    Configures the root logger so all loggers (including
    tripraft.requests and library loggers) use the same handler.
    """
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    is_production = app.config.get('FLASK_ENV', 'development') != 'development'

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if is_production:
        console_handler.setFormatter(JSONFormatter())
    else:
        log_format = app.config.get('LOG_FORMAT')
        console_handler.setFormatter(logging.Formatter(log_format))

    # Configure root logger so ALL loggers inherit this handler
    root = logging.getLogger()
    root.setLevel(log_level)
    # Remove any existing handlers to avoid duplicates on reloads
    root.handlers.clear()
    root.addHandler(console_handler)

    # Also configure Flask's app logger
    app.logger.setLevel(log_level)
    # Prevent double logging by removing app.logger's default handlers
    app.logger.handlers.clear()
    app.logger.propagate = True

    # Suppress noisy werkzeug access logs (we have structured logging now)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
