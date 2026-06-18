"""widen daily_targets.mode CHECK constraint to include 'gain'

Revision ID: f3a4mode0001
Revises: e1f2auth0001
Create Date: 2026-06-17 22:30:00.000000

العمود mode مخزّن كـ VARCHAR مع قيد CHECK اسمه 'targetmode' (Enum غير أصلي).
لإضافة وضع 'gain' لازم نعيد بناء القيد ليسمح بالقيمة الجديدة. (يعمل على Postgres/Neon.)
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a4mode0001"
down_revision: Union[str, None] = "e1f2auth0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE daily_targets DROP CONSTRAINT IF EXISTS targetmode")
    op.create_check_constraint(
        "targetmode",
        "daily_targets",
        "mode IN ('loss', 'maintain', 'gain')",
    )


def downgrade() -> None:
    op.execute("ALTER TABLE daily_targets DROP CONSTRAINT IF EXISTS targetmode")
    op.create_check_constraint(
        "targetmode",
        "daily_targets",
        "mode IN ('loss', 'maintain')",
    )
