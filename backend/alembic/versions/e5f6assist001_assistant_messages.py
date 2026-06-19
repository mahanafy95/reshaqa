"""add assistant_messages table (persisted AI assistant conversation history)

Revision ID: e5f6assist001
Revises: d4e5issue001
Create Date: 2026-06-19 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6assist001"
down_revision: Union[str, None] = "d4e5issue001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistant_messages_user_id"), "assistant_messages", ["user_id"], unique=False
    )
    op.create_index(
        "ix_assistant_messages_user_created",
        "assistant_messages",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_messages_user_created", table_name="assistant_messages")
    op.drop_index(op.f("ix_assistant_messages_user_id"), table_name="assistant_messages")
    op.drop_table("assistant_messages")
