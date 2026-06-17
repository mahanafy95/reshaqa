"""تعبئة مكتبة الأكلات من بيانات البذرة — idempotent (آمن لإعادة التشغيل).

الاستخدام:  python -m scripts.seed_food_library
"""
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models.food import FoodLibrary
from app.services.data.food_seed import FOOD_SEED


def main() -> int:
    db = SessionLocal()
    added = updated = 0
    try:
        for item in FOOD_SEED:
            name = item["name_ar"].strip()
            existing = db.scalar(select(FoodLibrary).where(FoodLibrary.name_ar == name))
            if existing is None:
                db.add(
                    FoodLibrary(
                        name_ar=name,
                        calories_per_100=item["calories_per_100"],
                        protein=item.get("protein", 0),
                        carbs=item.get("carbs", 0),
                        fat=item.get("fat", 0),
                        region=item.get("region", "generic"),
                        household_unit_ar=item.get("household_unit_ar"),
                        household_grams=item.get("household_grams"),
                    )
                )
                added += 1
            else:
                existing.calories_per_100 = item["calories_per_100"]
                existing.protein = item.get("protein", 0)
                existing.carbs = item.get("carbs", 0)
                existing.fat = item.get("fat", 0)
                existing.region = item.get("region", "generic")
                existing.household_unit_ar = item.get("household_unit_ar")
                existing.household_grams = item.get("household_grams")
                updated += 1
        db.commit()
        total = db.scalar(select(FoodLibrary).order_by(FoodLibrary.id))
        count = len(db.scalars(select(FoodLibrary)).all())
        print(f"seed done: added={added}, updated={updated}, total_rows={count}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
