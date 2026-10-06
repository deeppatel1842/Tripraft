# Purpose: Read-only checks that reject unsupported legacy identifier storage.
"""Read-only checks that reject unsupported legacy identifier storage."""
from uuid import UUID

import sqlalchemy as sa


def _uuid_storage_type(column_type):
    return isinstance(column_type, sa.Uuid) or (
        isinstance(column_type, sa.CHAR) and column_type.length == 32
    )


def assert_uuid_storage(connection):
    """Reject integer IDs and corrupt SQLite payloads before changing DDL.

    A type cast cannot invent UUIDs for integer identities or preserve their
    dependent references. Conversion requires an explicit old-to-new map.
    SQLite also permits integer payloads inside CHAR(32) UUID columns; verify
    every non-null value rather than trusting the reflected column type.
    """
    inspector = sa.inspect(connection)
    table_columns = {
        table: {column['name']: column['type'] for column in inspector.get_columns(table)}
        for table in inspector.get_table_names() if table != 'alembic_version'
    }
    for table, columns in table_columns.items():
        primary_key = inspector.get_pk_constraint(table).get('constrained_columns') or []
        if primary_key == ['id'] and isinstance(columns['id'], sa.Integer):
            raise RuntimeError(
                f'Legacy integer primary keys remain in {table}. '
                'Refusing automatic UUID conversion; use a backup-tested identity mapping.'
            )
        for foreign_key in inspector.get_foreign_keys(table):
            parent_columns = table_columns.get(foreign_key['referred_table'], {})
            for child, parent in zip(foreign_key['constrained_columns'], foreign_key['referred_columns']):
                if _uuid_storage_type(parent_columns.get(parent)) and not _uuid_storage_type(columns[child]):
                    raise RuntimeError(f'Incompatible UUID foreign key storage: {table}.{child}')
        if connection.dialect.name != 'sqlite':
            continue
        for name, column_type in columns.items():
            if not _uuid_storage_type(column_type):
                continue
            # Untyped expressions avoid ORM UUID conversion hiding bad data.
            column = sa.column(name)
            rows = connection.execute(
                sa.select(column).select_from(sa.table(table)).where(column.is_not(None))
            )
            try:
                for row in rows:
                    try:
                        parsed = UUID(str(row[0]))
                        # SQLAlchemy binds SQLite UUIDs as lowercase hex.
                        # Hyphenated/uppercase storage parses as a UUID but
                        # cannot be found by the ORM's canonical comparisons.
                        if str(row[0]) != parsed.hex:
                            raise ValueError('Non-canonical UUID storage')
                    except (ValueError, TypeError, AttributeError):
                        raise RuntimeError(
                            f'Invalid UUID payload or non-canonical storage in {table}.{name}; '
                            'repair identities and dependent references before upgrading.'
                        ) from None
            finally:
                rows.close()
