"""audit fix: soy milk 45 -> 39 kcal/100ml (matches Alpro Soya Original sweetened)

Revision ID: f8c9audit001
Revises: f7b8verde001
Create Date: 2026-06-19 16:00:00.000000

Nutrition audit (USDA / Alpro / Almarai / Open Food Facts) found the seeded soy milk
value (45) didn't match any standard; macros match Alpro Soya Original (sweetened) at
39 kcal/100ml. Other added products verified accurate within authoritative ranges.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8c9audit001"
down_revision: Union[str, None] = "f7b8verde001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL = (
    "UPDATE food_library SET calories_per_100=:c, protein=:p, carbs=:cb, fat=:f "
    "WHERE name_ar=:n"
)


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(_SQL),
        {"n": "حليب صويا", "c": 39, "p": 3.0, "cb": 2.5, "f": 1.8},
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(_SQL),
        {"n": "حليب صويا", "c": 45, "p": 3.3, "cb": 2.5, "f": 1.8},
    )
