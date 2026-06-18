"""add email + google_sub to users, nullable password_hash, password_resets table

Revision ID: e1f2auth0001
Revises: c7d2admin0001
Create Date: 2026-06-17 21:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2auth0001"
down_revision: Union[str, None] = "c7d2admin0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # أعمدة جديدة على users
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("google_sub", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_google_sub"), "users", ["google_sub"], unique=True)

    # كلمة السر تصبح اختيارية (حسابات جوجل بدون كلمة سر)
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)

    # جدول رموز إعادة التعيين
    op.create_table(
        "password_resets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("used", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_password_resets_user_id"), "password_resets", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_password_resets_user_id"), table_name="password_resets")
    op.drop_table("password_resets")
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
    op.drop_index(op.f("ix_users_google_sub"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "email")
