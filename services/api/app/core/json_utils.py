# Purpose: JSON-boundary helpers for values emitted by ORM-backed services.
"""JSON-boundary helpers for values emitted by ORM-backed services."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


def json_safe(value):
    """Return a JSON-serializable copy without mutating caller-owned data.

    Activity and notification payloads are assembled by many services.  UUIDs
    are common in those payloads but are not supported by every SQLAlchemy JSON
    dialect/serializer, so normalize them at the model boundary.
    """
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return value
