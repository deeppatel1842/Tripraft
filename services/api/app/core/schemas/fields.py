# Purpose: Shared marshmallow field types. Every identifier in this codebase is a UUIDv7 string (see.
"""Shared marshmallow field types.

Every identifier in this codebase is a UUIDv7 string (see
``app.core.db.uuid7``). Schemas previously declared them as
``fields.Integer`` left over from the pre-UUID schema, which rejected every
real ID with a 422. ``UUIDString`` is the one place that contract is defined,
so the validation and the error message are identical everywhere.
"""
from uuid import UUID

from marshmallow import ValidationError, fields


class UUIDString(fields.Field):
    """A UUID accepted as a string and deserialised to a ``uuid.UUID``.

    Accepts a ``uuid.UUID`` or any string ``uuid.UUID`` can parse (hyphenated,
    braced, urn-prefixed, or bare hex).

    It deserialises to a ``uuid.UUID`` object, not a string, because that is
    what the rest of the backend already holds: the auth decorators put a
    ``uuid.UUID`` in ``g.user_id`` and SQLAlchemy returns ``uuid.UUID`` from
    every ID column. Handing the service layer a string instead would make
    ordinary comparisons such as ``expense.created_by == user_id`` silently
    false -- the same mixed-type defect this migration exists to remove.
    Serialisation still emits a string, and Flask's JSON provider renders
    ``uuid.UUID`` as one.

    Integers are rejected: an integer ID is always a caller still on the
    pre-UUID contract, and silently coercing one would look up the wrong row
    or none at all.
    """

    default_error_messages = {
        'invalid_uuid': 'Not a valid UUID.',
    }

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, UUID):
            return value
        if not isinstance(value, str):
            raise self.make_error('invalid_uuid')
        try:
            return UUID(value.strip())
        except (ValueError, AttributeError, TypeError):
            raise self.make_error('invalid_uuid') from None


__all__ = ['UUIDString']
