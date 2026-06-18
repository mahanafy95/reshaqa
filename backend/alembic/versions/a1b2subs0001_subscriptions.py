"""add subscriptions table (Google Play premium entitlement)

Revision ID: a1b2subs0001
Revises: f3a4mode0001
Create Date: 2026-06-17 23:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2subs0001"
down_revision: Union[str, None] = "f3a4mode0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("product_id", sa.String(length=120), nullable=True),
        sa.Column("purchase_token", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_renewing", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_subscription_user"),
        sa.UniqueConstraint("purchase_token", name="uq_subscription_token"),
    )
    op.create_index(op.f("ix_subscriptions_user_id"), "subscriptions", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_subscriptions_user_id"), table_name="subscriptions")
    op.drop_table("subscriptions")
