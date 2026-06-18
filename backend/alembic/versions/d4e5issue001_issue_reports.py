"""add issue_reports table (user-submitted problem reports)

Revision ID: d4e5issue001
Revises: c3d4social01
Create Date: 2026-06-18 01:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5issue001"
down_revision: Union[str, None] = "c3d4social01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "issue_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_issue_reports_user_id"), "issue_reports", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_issue_reports_user_id"), table_name="issue_reports")
    op.drop_table("issue_reports")
