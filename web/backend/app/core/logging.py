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
        if record.exc_info and record.exc_info[0]:
            log_entry['exception'] = self.formatException(record.exc_info)
        return _json.dumps(log_entry, default=str)


def setup_logging(app):
    """
    Configure application logging.

    In production (FLASK_ENV != 'development'), logs are emitted as
    single-line JSON for easy ingestion by log aggregators.  In
    development the human-readable format from config is used.
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

    # Configure root logger
    app.logger.setLevel(log_level)
    app.logger.addHandler(console_handler)

    # Set werkzeug logger to warning only
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
