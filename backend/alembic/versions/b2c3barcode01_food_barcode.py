"""add barcode column to food_library + seed common energy drinks

Revision ID: b2c3barcode01
Revises: a1b2subs0001
Create Date: 2026-06-17 23:55:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import column, table

# revision identifiers, used by Alembic.
revision: str = "b2c3barcode01"
down_revision: Union[str, None] = "a1b2subs0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# مشروبات الطاقة الشائعة (القيم لكل 100 مل). الباركود لأشهر الإصدارات العالمية —
# لو علبة المستخدم بباركود مختلف، التطبيق بيسمحله يحفظها مرة وتتعرف بعد كده.
_ENERGY_DRINKS = [
    {"name_ar": "ريد بُل", "barcode": "9002490100070", "calories_per_100": 45, "protein": 0, "carbs": 11, "fat": 0},
    {"name_ar": "ريد بُل خالي السكر", "barcode": "9002490205201", "calories_per_100": 3, "protein": 0, "carbs": 0, "fat": 0},
    {"name_ar": "مونستر طاقة", "barcode": "070847811169", "calories_per_100": 47, "protein": 0, "carbs": 12, "fat": 0},
    {"name_ar": "باور هورس", "barcode": "9002859000034", "calories_per_100": 48, "protein": 0, "carbs": 12, "fat": 0},
    {"name_ar": "XL طاقة", "barcode": None, "calories_per_100": 48, "protein": 0, "carbs": 12, "fat": 0},
    {"name_ar": "تايجر طاقة", "barcode": None, "calories_per_100": 49, "protein": 0, "carbs": 12, "fat": 0},
    {"name_ar": "كود ريد طاقة", "barcode": None, "calories_per_100": 50, "protein": 0, "carbs": 13, "fat": 0},
    {"name_ar": "هيل طاقة", "barcode": None, "calories_per_100": 50, "protein": 0, "carbs": 13, "fat": 0},
]


def upgrade() -> None:
    op.add_column("food_library", sa.Column("barcode", sa.String(length=20), nullable=True))
    op.create_index(op.f("ix_food_library_barcode"), "food_library", ["barcode"], unique=False)

    fl = table(
        "food_library",
        column("name_ar", sa.String),
        column("barcode", sa.String),
        column("calories_per_100", sa.Float),
        column("protein", sa.Float),
        column("carbs", sa.Float),
        column("fat", sa.Float),
        column("region", sa.String),
        column("household_unit_ar", sa.String),
        column("household_grams", sa.Float),
    )
    op.bulk_insert(
        fl,
        [
            {
                "name_ar": d["name_ar"],
                "barcode": d["barcode"],
                "calories_per_100": d["calories_per_100"],
                "protein": d["protein"],
                "carbs": d["carbs"],
                "fat": d["fat"],
                "region": "generic",
                "household_unit_ar": "علبة",
                "household_grams": 250,  # العلبة الشائعة ~250 مل
            }
            for d in _ENERGY_DRINKS
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_food_library_barcode"), table_name="food_library")
    op.drop_column("food_library", "barcode")
