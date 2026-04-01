"""
One-time migration: add suggested_time to gp_places, create gp_vault_documents.

Run with:
    python -m app.migrations.add_vault_and_time
"""

import logging
from app.infrastructure.db.connection import engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


def migrate():
    with engine.connect() as conn:
        # Add suggested_time column to gp_places (safe: skip if exists)
        try:
            conn.execute(text(
                "ALTER TABLE gp_places ADD COLUMN suggested_time VARCHAR(10)"
            ))
            conn.commit()
            print("Added suggested_time column to gp_places")
        except Exception:
            conn.rollback()
            print("suggested_time column already exists or failed — skipping")

        # Create gp_vault_documents table (safe: IF NOT EXISTS)
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS gp_vault_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL REFERENCES travel_groups(id) ON DELETE CASCADE,
                    filename VARCHAR(255) NOT NULL,
                    original_filename VARCHAR(255) NOT NULL,
                    mime_type VARCHAR(100) NOT NULL,
                    file_size INTEGER NOT NULL,
                    uploaded_by INTEGER NOT NULL REFERENCES users(id),
                    is_deleted BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_gp_vault_group ON gp_vault_documents (group_id, is_deleted)"
            ))
            conn.commit()
            print("Created gp_vault_documents table")
        except Exception as e:
            conn.rollback()
            print(f"gp_vault_documents migration error: {e}")


if __name__ == '__main__':
    migrate()
