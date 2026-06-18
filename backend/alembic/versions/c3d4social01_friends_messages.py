"""add friendships + messages tables (community: friends + chat)

Revision ID: c3d4social01
Revises: b2c3barcode01
Create Date: 2026-06-18 00:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4social01"
down_revision: Union[str, None] = "b2c3barcode01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("addressee_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["addressee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
    )
    op.create_index(op.f("ix_friendships_requester_id"), "friendships", ["requester_id"], unique=False)
    op.create_index(op.f("ix_friendships_addressee_id"), "friendships", ["addressee_id"], unique=False)
    op.create_index("ix_friendship_addressee_status", "friendships", ["addressee_id", "status"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(length=2000), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_sender_id"), "messages", ["sender_id"], unique=False)
    op.create_index(op.f("ix_messages_recipient_id"), "messages", ["recipient_id"], unique=False)
    op.create_index("ix_message_pair_time", "messages", ["sender_id", "recipient_id", "created_at"], unique=False)
    op.create_index("ix_message_recipient_unread", "messages", ["recipient_id", "read_at"], unique=False)


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("friendships")
