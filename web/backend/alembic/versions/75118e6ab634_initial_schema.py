"""initial_schema

Revision ID: 75118e6ab634
Revises: 
Create Date: 2026-03-19 15:24:47.952398

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '75118e6ab634'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — baseline stamp, no-op."""


def downgrade() -> None:
    """Downgrade schema — baseline stamp, no-op."""
