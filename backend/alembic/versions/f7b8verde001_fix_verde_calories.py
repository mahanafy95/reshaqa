"""fix Verde chocolate calories — it's sugar-free (stevia), much lower than regular chocolate

Revision ID: f7b8verde001
Revises: f6a7saudi001
Create Date: 2026-06-19 15:00:00.000000

Earlier seed used standard (sugary) chocolate values (~535-580 kcal/100g). Verde is an
Egyptian SUGAR-FREE, stevia-sweetened keto line. The only published source is the
physical label (Verde does not publish per-100g nutrition online — verified across the
official site, verde-egy.shop, Gulf retailers, Open Food Facts, and aggregators).
Owner's in-hand label (Classic Hazelnut): 80g bar = 18 squares = 204 kcal => 255 kcal/100g.
Other variants anchored to the same value (same keto line) until exact labels are available.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7b8verde001"
down_revision: Union[str, None] = "f6a7saudi001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (name_ar, calories_per_100, protein, carbs, fat) — corrected for the sugar-free line.
# Hazelnut calories CONFIRMED from the label; others anchored to it (best estimate).
_CORRECTED = [
    ("شوكولاتة فيردي بالبندق", 255, 6.5, 14.0, 19.0),
    ("شوكولاتة فيردي دارك", 255, 6.0, 15.0, 19.0),
    ("شوكولاتة فيردي بالحليب", 255, 6.0, 16.0, 18.0),
    ("شوكولاتة فيردي أبيض", 260, 6.0, 18.0, 19.0),
]

# القيم القديمة الخاطئة (شوكولاتة عادية بسكر) — للرجوع لو لزم.
_PREVIOUS = [
    ("شوكولاتة فيردي بالبندق", 560, 8.0, 52.0, 35.0),
    ("شوكولاتة فيردي دارك", 580, 7.8, 46.0, 43.0),
    ("شوكولاتة فيردي بالحليب", 535, 7.7, 57.0, 30.0),
    ("شوكولاتة فيردي أبيض", 560, 6.0, 59.0, 33.0),
]

_UPDATE = (
    "UPDATE food_library SET calories_per_100=:c, protein=:p, carbs=:cb, fat=:f, "
    "household_unit_ar='مربع', household_grams=5 WHERE name_ar=:n"
)


def _apply(rows) -> None:
    conn = op.get_bind()
    for name, cal, p, cb, f in rows:
        conn.execute(sa.text(_UPDATE), {"n": name, "c": cal, "p": p, "cb": cb, "f": f})


def upgrade() -> None:
    _apply(_CORRECTED)


def downgrade() -> None:
    _apply(_PREVIOUS)
