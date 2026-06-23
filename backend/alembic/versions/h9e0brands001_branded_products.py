"""seed common branded products (Egypt/Gulf) so Arabic brand names resolve at high
confidence instead of falling back to the heuristic default (~120 kcal).

Revision ID: h9e0brands001
Revises: g8d9diet001
Create Date: 2026-06-23 18:00:00.000000

Why: live audit found that popular packaged products typed by Arabic name (نوتيلا،
بيبسي، اندومي، كيت كات ...) were NOT in the library and NOT found by OpenFoodFacts
(OFF only matches Latin product names; its Arabic entries usually lack nutriments),
and the Gemini web-lookup is only active when GEMINI_API_KEY is configured. Result:
these products returned the heuristic default ~120 kcal — clearly wrong for a candy
bar or chocolate spread. Seeding them fixes the most common cases now, for free,
independent of any API key.

Values are standard manufacturer / USDA per-100g (solids) or per-100ml (drinks)
references. Idempotent: inserts each only if its name_ar isn't already present.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h9e0brands001"
down_revision: Union[str, None] = "g8d9diet001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PRODUCTS = [
    # ===== شوكولاتة وسناكس معبّأة — لكل 100 جرام =====
    {"name_ar": "نوتيلا", "calories_per_100": 539, "protein": 6.3, "carbs": 57.5, "fat": 30.9, "region": "generic", "household_unit_ar": "ملعقة كبيرة", "household_grams": 15},
    {"name_ar": "كيندر بوينو", "calories_per_100": 571, "protein": 8.5, "carbs": 49.5, "fat": 37.3, "region": "generic", "household_unit_ar": "إصبع", "household_grams": 22},
    {"name_ar": "كيت كات", "calories_per_100": 518, "protein": 5.9, "carbs": 61.0, "fat": 27.0, "region": "generic", "household_unit_ar": "إصبعين", "household_grams": 20},
    {"name_ar": "سنيكرز", "calories_per_100": 491, "protein": 8.0, "carbs": 57.0, "fat": 24.0, "region": "generic", "household_unit_ar": "قطعة", "household_grams": 50},
    {"name_ar": "مارس", "calories_per_100": 449, "protein": 3.8, "carbs": 70.0, "fat": 17.0, "region": "generic", "household_unit_ar": "قطعة", "household_grams": 51},
    {"name_ar": "جالاكسي", "calories_per_100": 545, "protein": 6.5, "carbs": 57.0, "fat": 32.0, "region": "generic", "household_unit_ar": "قطعة", "household_grams": 40},
    {"name_ar": "اوريو", "calories_per_100": 480, "protein": 5.0, "carbs": 71.0, "fat": 20.0, "region": "generic", "household_unit_ar": "قطعة", "household_grams": 11},
    {"name_ar": "بسكويت سادة", "calories_per_100": 460, "protein": 7.0, "carbs": 70.0, "fat": 16.0, "region": "generic", "household_unit_ar": "قطعة", "household_grams": 10},
    {"name_ar": "ويفر", "calories_per_100": 510, "protein": 5.0, "carbs": 63.0, "fat": 27.0, "region": "generic", "household_unit_ar": "قطعة", "household_grams": 30},
    {"name_ar": "كرواسون", "calories_per_100": 406, "protein": 8.2, "carbs": 45.8, "fat": 21.0, "region": "generic", "household_unit_ar": "قطعة", "household_grams": 60},

    # ===== سبريدات وحبوب — لكل 100 جرام =====
    {"name_ar": "زبدة فول سوداني", "calories_per_100": 588, "protein": 25.0, "carbs": 20.0, "fat": 50.0, "region": "generic", "household_unit_ar": "ملعقة كبيرة", "household_grams": 16},
    {"name_ar": "مربى", "calories_per_100": 250, "protein": 0.4, "carbs": 65.0, "fat": 0.1, "region": "generic", "household_unit_ar": "ملعقة كبيرة", "household_grams": 20},
    {"name_ar": "كورن فليكس", "calories_per_100": 357, "protein": 7.0, "carbs": 84.0, "fat": 0.9, "region": "generic", "household_unit_ar": "كوب", "household_grams": 30},

    # ===== مشروبات غازية وطاقة وعصائر — لكل 100 مل =====
    {"name_ar": "بيبسي", "calories_per_100": 43, "protein": 0.0, "carbs": 11.0, "fat": 0.0, "region": "generic", "household_unit_ar": "علبة", "household_grams": 330},
    {"name_ar": "كوكا كولا", "calories_per_100": 42, "protein": 0.0, "carbs": 10.6, "fat": 0.0, "region": "generic", "household_unit_ar": "علبة", "household_grams": 330},
    {"name_ar": "سبرايت", "calories_per_100": 39, "protein": 0.0, "carbs": 9.7, "fat": 0.0, "region": "generic", "household_unit_ar": "علبة", "household_grams": 330},
    {"name_ar": "سفن اب", "calories_per_100": 41, "protein": 0.0, "carbs": 10.4, "fat": 0.0, "region": "generic", "household_unit_ar": "علبة", "household_grams": 330},
    {"name_ar": "ميرندا", "calories_per_100": 49, "protein": 0.0, "carbs": 12.0, "fat": 0.0, "region": "generic", "household_unit_ar": "علبة", "household_grams": 330},
    {"name_ar": "ريد بُل", "calories_per_100": 45, "protein": 0.0, "carbs": 11.3, "fat": 0.0, "region": "generic", "household_unit_ar": "علبة", "household_grams": 250},
    {"name_ar": "عصير برتقان", "calories_per_100": 45, "protein": 0.7, "carbs": 10.4, "fat": 0.2, "region": "generic", "household_unit_ar": "كوب", "household_grams": 240},

    # ===== أطباق سريعة شائعة — لكل 100 جرام =====
    {"name_ar": "اندومي", "calories_per_100": 450, "protein": 9.0, "carbs": 61.0, "fat": 18.0, "region": "generic", "household_unit_ar": "عبوة", "household_grams": 70},
    {"name_ar": "نسكافيه ٣ في ١", "calories_per_100": 454, "protein": 5.0, "carbs": 75.0, "fat": 12.0, "region": "generic", "household_unit_ar": "ظرف", "household_grams": 20},
    {"name_ar": "بيتزا", "calories_per_100": 240, "protein": 10.0, "carbs": 30.0, "fat": 8.0, "region": "generic", "household_unit_ar": "شريحة", "household_grams": 120},
    {"name_ar": "برجر", "calories_per_100": 250, "protein": 15.0, "carbs": 20.0, "fat": 12.0, "region": "generic", "household_unit_ar": "ساندويتش", "household_grams": 150},
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
