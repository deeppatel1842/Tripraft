# Purpose: UUIDv7 Generator (RFC 9562) Time-ordered, globally unique, cryptographically random identifiers.
"""
UUIDv7 Generator (RFC 9562)
============================
Time-ordered, globally unique, cryptographically random identifiers.

Why UUIDv7:
- Non-sequential: Cannot enumerate or guess IDs (unlike auto-increment integers)
- Time-ordered: Monotonically increasing, B-tree friendly for database indexes
- 128-bit: 2^128 possible values — collision probability is negligible
- Sortable: Natural chronological ordering from embedded timestamp
- Standard: PostgreSQL native UUID type (16 bytes) / SQLite CHAR(32)

Layout (128 bits):
  Bits 0-47:   Unix timestamp in milliseconds (48 bits)
  Bits 48-51:  Version = 0b0111 (4 bits)
  Bits 52-63:  Cryptographic random (12 bits)
  Bits 64-65:  Variant = 0b10 (2 bits)
  Bits 66-127: Cryptographic random (62 bits)
"""
import os
import time
from uuid import UUID

from sqlalchemy import Uuid as _SaUuid
from sqlalchemy.types import TypeDecorator


class CoercingUuid(TypeDecorator):
    """Uuid type that auto-coerces plain strings to uuid.UUID objects.

    Drop-in replacement for sqlalchemy.Uuid. Prevents
    "'str' object has no attribute 'hex'" when URL-derived or
    JWT-derived string IDs reach filter() / .get() calls.
    """
    impl = _SaUuid
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and isinstance(value, str):
            return UUID(value)
        return value


def uuid7() -> UUID:
    """Generate a UUIDv7 identifier."""
    timestamp_ms = int(time.time() * 1000)

    # 48-bit Unix timestamp (milliseconds)
    ts = timestamp_ms.to_bytes(6, 'big')

    # Version 7 (4 bits) + 12 random bits
    rand_a = bytearray(os.urandom(2))
    rand_a[0] = 0x70 | (rand_a[0] & 0x0F)

    # Variant 10 (2 bits) + 62 random bits
    rand_b = bytearray(os.urandom(8))
    rand_b[0] = 0x80 | (rand_b[0] & 0x3F)

    return UUID(bytes=ts + bytes(rand_a) + bytes(rand_b))
