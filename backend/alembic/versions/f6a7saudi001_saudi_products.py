"""seed common Saudi/Gulf products missing from the library (almond/lactose-free milk, Verde chocolate)

Revision ID: f6a7saudi001
Revises: e5f6assist001
Create Date: 2026-06-19 14:00:00.000000

Idempotent: inserts each product only if its name_ar isn't already present.
Values are standard per-100g/100ml references for the product type.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7saudi001"
down_revision: Union[str, None] = "e5f6assist001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PRODUCTS = [
    # ===== ألبان بديلة / خالية اللاكتوز (شائعة في السعودية) — لكل 100 مل =====
    {"name_ar": "حليب لوز", "calories_per_100": 24, "protein": 0.5, "carbs": 3.0, "fat": 1.1, "region": "generic", "household_unit_ar": "كوب", "household_grams": 240},
    {"name_ar": "حليب لوز غير محلّى", "calories_per_100": 15, "protein": 0.5, "carbs": 0.6, "fat": 1.2, "region": "generic", "household_unit_ar": "كوب", "household_grams": 240},
    {"name_ar": "حليب خالي اللاكتوز", "calories_per_100": 62, "protein": 3.3, "carbs": 4.8, "fat": 3.4, "region": "generic", "household_unit_ar": "كوب", "household_grams": 240},
    {"name_ar": "حليب خالي اللاكتوز قليل الدسم", "calories_per_100": 47, "protein": 3.4, "carbs": 5.0, "fat": 1.5, "region": "generic", "household_unit_ar": "كوب", "household_grams": 240},
    {"name_ar": "حليب صويا", "calories_per_100": 45, "protein": 3.3, "carbs": 2.5, "fat": 1.8, "region": "generic", "household_unit_ar": "كوب", "household_grams": 240},
    # ===== شوكولاتة فيردي (Verde) — قيم مرجعية حسب نوع الشوكولاتة، لكل 100 جرام =====
    {"name_ar": "شوكولاتة فيردي دارك", "calories_per_100": 580, "protein": 7.8, "carbs": 46.0, "fat": 43.0, "region": "sa", "household_unit_ar": "قطعة", "household_grams": 25},
    {"name_ar": "شوكولاتة فيردي بالحليب", "calories_per_100": 535, "protein": 7.7, "carbs": 57.0, "fat": 30.0, "region": "sa", "household_unit_ar": "قطعة", "household_grams": 25},
    {"name_ar": "شوكولاتة فيردي بالبندق", "calories_per_100": 560, "protein": 8.0, "carbs": 52.0, "fat": 35.0, "region": "sa", "household_unit_ar": "قطعة", "household_grams": 25},
    {"name_ar": "شوكولاتة فيردي أبيض", "calories_per_100": 560, "protein": 6.0, "carbs": 59.0, "fat": 33.0, "region": "sa", "household_unit_ar": "قطعة", "household_grams": 25},
]

_NAMES = tuple(p["name_ar"] for p in _PRODUCTS)


def upgrade() -> None:
    conn = op.get_bind()
    for p in _PRODUCTS:
        exists = conn.execute(
            sa.text("SELECT 1 FROM food_library WHERE name_ar = :n LIMIT 1"), {"n": p["name_ar"]}
        ).first()
        if exists:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO food_library "
                "(name_ar, calories_per_100, protein, carbs, fat, region, household_unit_ar, household_grams) "
                "VALUES (:name_ar, :calories_per_100, :protein, :carbs, :fat, :region, "
                ":household_unit_ar, :household_grams)"
            ),
            p,
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM food_library WHERE name_ar IN :names").bindparams(
            sa.bindparam("names", expanding=True)
        ),
        {"names": list(_NAMES)},
    )
