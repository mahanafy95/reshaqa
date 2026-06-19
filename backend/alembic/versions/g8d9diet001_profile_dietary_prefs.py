"""add dietary_pref + allergies to profiles (AI assistant respects them)

Revision ID: g8d9diet001
Revises: f8c9audit001
Create Date: 2026-06-19 17:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g8d9diet001"
down_revision: Union[str, None] = "f8c9audit001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("dietary_pref", sa.String(length=20), nullable=False, server_default="none"),
    )
    op.add_column("profiles", sa.Column("allergies", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "allergies")
    op.drop_column("profiles", "dietary_pref")
