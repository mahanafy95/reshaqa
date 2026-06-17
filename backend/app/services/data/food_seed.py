"""بيانات بذرة لمكتبة الأكلات (قيم تقريبية لكل 100 جرام).

ملاحظة: هذه قيم مرجعية تقريبية للتوعية.
المصدر الأساسي ملف food_library.json (مولّد، ~330 صنف). القائمة أدناه احتياطية
تُستخدم فقط لو لم يوجد ملف JSON.
كل عنصر: name_ar, calories_per_100, protein, carbs, fat, region, household_unit_ar, household_grams
"""
import json
from pathlib import Path

_JSON_PATH = Path(__file__).parent / "food_library.json"

_BASE_SEED: list[dict] = [
    # ===== أطباق مصرية =====
    {"name_ar": "كشري", "calories_per_100": 150, "protein": 5.0, "carbs": 28.0, "fat": 2.5, "region": "eg", "household_unit_ar": "طبق وسط", "household_grams": 350},
    {"name_ar": "ملوخية", "calories_per_100": 60, "protein": 4.0, "carbs": 5.0, "fat": 2.5, "region": "eg", "household_unit_ar": "طبق", "household_grams": 250},
    {"name_ar": "فول مدمس", "calories_per_100": 110, "protein": 7.5, "carbs": 15.0, "fat": 2.5, "region": "eg", "household_unit_ar": "طبق", "household_grams": 200},
    {"name_ar": "طعمية", "calories_per_100": 330, "protein": 13.0, "carbs": 30.0, "fat": 18.0, "region": "eg", "household_unit_ar": "قرص", "household_grams": 30},
    {"name_ar": "محشي ورق عنب", "calories_per_100": 180, "protein": 3.0, "carbs": 22.0, "fat": 9.0, "region": "eg", "household_unit_ar": "حبة", "household_grams": 20},
    {"name_ar": "مكرونة بشاميل", "calories_per_100": 200, "protein": 9.0, "carbs": 22.0, "fat": 9.0, "region": "eg", "household_unit_ar": "قطعة", "household_grams": 250},
    {"name_ar": "بامية باللحمة", "calories_per_100": 110, "protein": 7.0, "carbs": 8.0, "fat": 6.0, "region": "eg", "household_unit_ar": "طبق", "household_grams": 250},
    {"name_ar": "حواوشي", "calories_per_100": 260, "protein": 14.0, "carbs": 22.0, "fat": 13.0, "region": "eg", "household_unit_ar": "ربع رغيف", "household_grams": 150},
    {"name_ar": "كبدة إسكندراني", "calories_per_100": 200, "protein": 20.0, "carbs": 5.0, "fat": 11.0, "region": "eg", "household_unit_ar": "طبق", "household_grams": 150},

    # ===== أطباق سعودية/خليجية =====
    {"name_ar": "كبسة دجاج", "calories_per_100": 170, "protein": 9.0, "carbs": 20.0, "fat": 6.0, "region": "sa", "household_unit_ar": "صحن", "household_grams": 400},
    {"name_ar": "كبسة لحم", "calories_per_100": 190, "protein": 9.0, "carbs": 20.0, "fat": 8.5, "region": "sa", "household_unit_ar": "صحن", "household_grams": 400},
    {"name_ar": "مندي دجاج", "calories_per_100": 175, "protein": 10.0, "carbs": 19.0, "fat": 6.5, "region": "sa", "household_unit_ar": "صحن", "household_grams": 400},
    {"name_ar": "جريش", "calories_per_100": 130, "protein": 5.0, "carbs": 18.0, "fat": 4.0, "region": "sa", "household_unit_ar": "صحن", "household_grams": 300},
    {"name_ar": "مرقوق", "calories_per_100": 140, "protein": 6.0, "carbs": 18.0, "fat": 4.5, "region": "sa", "household_unit_ar": "صحن", "household_grams": 300},
    {"name_ar": "مطبق", "calories_per_100": 300, "protein": 9.0, "carbs": 30.0, "fat": 16.0, "region": "sa", "household_unit_ar": "قطعة", "household_grams": 120},
    {"name_ar": "تميس", "calories_per_100": 280, "protein": 8.0, "carbs": 50.0, "fat": 5.0, "region": "sa", "household_unit_ar": "رغيف", "household_grams": 120},
    {"name_ar": "لقيمات", "calories_per_100": 360, "protein": 5.0, "carbs": 50.0, "fat": 16.0, "region": "sa", "household_unit_ar": "حبة", "household_grams": 15},

    # ===== حبوب وخبز =====
    {"name_ar": "رز أبيض مطبوخ", "calories_per_100": 130, "protein": 2.7, "carbs": 28.0, "fat": 0.3, "region": "generic", "household_unit_ar": "كوب", "household_grams": 160},
    {"name_ar": "عيش بلدي", "calories_per_100": 250, "protein": 9.0, "carbs": 50.0, "fat": 1.5, "region": "eg", "household_unit_ar": "رغيف", "household_grams": 90},
    {"name_ar": "خبز أبيض", "calories_per_100": 265, "protein": 9.0, "carbs": 49.0, "fat": 3.2, "region": "generic", "household_unit_ar": "شريحة", "household_grams": 30},
    {"name_ar": "شوفان", "calories_per_100": 380, "protein": 13.0, "carbs": 67.0, "fat": 7.0, "region": "generic", "household_unit_ar": "كوب جاف", "household_grams": 80},
    {"name_ar": "عدس مطبوخ", "calories_per_100": 115, "protein": 9.0, "carbs": 20.0, "fat": 0.4, "region": "generic", "household_unit_ar": "كوب", "household_grams": 200},
    {"name_ar": "مكرونة مسلوقة", "calories_per_100": 158, "protein": 5.8, "carbs": 31.0, "fat": 0.9, "region": "generic", "household_unit_ar": "كوب", "household_grams": 140},

    # ===== بروتينات =====
    {"name_ar": "صدر دجاج مشوي", "calories_per_100": 165, "protein": 31.0, "carbs": 0.0, "fat": 3.6, "region": "generic", "household_unit_ar": "قطعة", "household_grams": 120},
    {"name_ar": "لحم بقري مشوي", "calories_per_100": 250, "protein": 26.0, "carbs": 0.0, "fat": 17.0, "region": "generic", "household_unit_ar": "قطعة", "household_grams": 100},
    {"name_ar": "سمك مشوي", "calories_per_100": 130, "protein": 22.0, "carbs": 0.0, "fat": 4.5, "region": "generic", "household_unit_ar": "سمكة وسط", "household_grams": 150},
    {"name_ar": "تونة بالماء", "calories_per_100": 116, "protein": 26.0, "carbs": 0.0, "fat": 1.0, "region": "generic", "household_unit_ar": "علبة", "household_grams": 80},
    {"name_ar": "بيض مسلوق", "calories_per_100": 155, "protein": 13.0, "carbs": 1.1, "fat": 11.0, "region": "generic", "household_unit_ar": "بيضة", "household_grams": 50},

    # ===== ألبان =====
    {"name_ar": "لبن كامل الدسم", "calories_per_100": 61, "protein": 3.2, "carbs": 4.8, "fat": 3.3, "region": "generic", "household_unit_ar": "كوب", "household_grams": 240},
    {"name_ar": "زبادي", "calories_per_100": 60, "protein": 3.5, "carbs": 5.0, "fat": 3.0, "region": "generic", "household_unit_ar": "علبة", "household_grams": 100},
    {"name_ar": "جبنة بيضاء", "calories_per_100": 260, "protein": 14.0, "carbs": 4.0, "fat": 21.0, "region": "eg", "household_unit_ar": "شريحة", "household_grams": 30},
    {"name_ar": "جبنة قريش", "calories_per_100": 98, "protein": 11.0, "carbs": 3.4, "fat": 4.3, "region": "eg", "household_unit_ar": "ملعقة كبيرة", "household_grams": 30},

    # ===== خضار وفواكه =====
    {"name_ar": "سلطة خضراء", "calories_per_100": 25, "protein": 1.2, "carbs": 4.5, "fat": 0.3, "region": "generic", "household_unit_ar": "طبق", "household_grams": 150},
    {"name_ar": "بطاطس مسلوقة", "calories_per_100": 87, "protein": 1.9, "carbs": 20.0, "fat": 0.1, "region": "generic", "household_unit_ar": "حبة وسط", "household_grams": 150},
    {"name_ar": "موز", "calories_per_100": 89, "protein": 1.1, "carbs": 23.0, "fat": 0.3, "region": "generic", "household_unit_ar": "موزة", "household_grams": 120},
    {"name_ar": "تفاح", "calories_per_100": 52, "protein": 0.3, "carbs": 14.0, "fat": 0.2, "region": "generic", "household_unit_ar": "تفاحة", "household_grams": 180},
    {"name_ar": "تمر", "calories_per_100": 282, "protein": 2.5, "carbs": 75.0, "fat": 0.4, "region": "generic", "household_unit_ar": "حبة", "household_grams": 8},

    # ===== مشروبات =====
    {"name_ar": "شاي بسكر", "calories_per_100": 30, "protein": 0.0, "carbs": 7.5, "fat": 0.0, "region": "generic", "household_unit_ar": "كوب", "household_grams": 200},
    {"name_ar": "قهوة عربية", "calories_per_100": 2, "protein": 0.1, "carbs": 0.3, "fat": 0.0, "region": "sa", "household_unit_ar": "فنجان", "household_grams": 60},
    {"name_ar": "عصير برتقال", "calories_per_100": 45, "protein": 0.7, "carbs": 10.0, "fat": 0.2, "region": "generic", "household_unit_ar": "كوب", "household_grams": 240},
    {"name_ar": "مشروب غازي", "calories_per_100": 42, "protein": 0.0, "carbs": 11.0, "fat": 0.0, "region": "generic", "household_unit_ar": "علبة", "household_grams": 330},
    {"name_ar": "ماء", "calories_per_100": 0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "region": "generic", "household_unit_ar": "كوب", "household_grams": 250},

    # ===== حلويات =====
    {"name_ar": "كنافة", "calories_per_100": 350, "protein": 6.0, "carbs": 45.0, "fat": 16.0, "region": "eg", "household_unit_ar": "قطعة", "household_grams": 150},
    {"name_ar": "بسبوسة", "calories_per_100": 340, "protein": 4.0, "carbs": 52.0, "fat": 13.0, "region": "eg", "household_unit_ar": "قطعة", "household_grams": 80},
    {"name_ar": "رز بلبن", "calories_per_100": 130, "protein": 3.5, "carbs": 22.0, "fat": 3.0, "region": "eg", "household_unit_ar": "كوب", "household_grams": 200},

    # ===== دهون ومكسرات وإضافات =====
    {"name_ar": "زيت زيتون", "calories_per_100": 884, "protein": 0.0, "carbs": 0.0, "fat": 100.0, "region": "generic", "household_unit_ar": "ملعقة كبيرة", "household_grams": 14},
    {"name_ar": "سمن", "calories_per_100": 900, "protein": 0.0, "carbs": 0.0, "fat": 100.0, "region": "generic", "household_unit_ar": "ملعقة كبيرة", "household_grams": 14},
    {"name_ar": "طحينة", "calories_per_100": 595, "protein": 17.0, "carbs": 21.0, "fat": 53.0, "region": "generic", "household_unit_ar": "ملعقة كبيرة", "household_grams": 15},
    {"name_ar": "عسل نحل", "calories_per_100": 304, "protein": 0.3, "carbs": 82.0, "fat": 0.0, "region": "generic", "household_unit_ar": "ملعقة كبيرة", "household_grams": 21},
    {"name_ar": "لوز", "calories_per_100": 579, "protein": 21.0, "carbs": 22.0, "fat": 50.0, "region": "generic", "household_unit_ar": "حفنة", "household_grams": 28},
]


def _load_seed() -> list[dict]:
    """يحمّل المكتبة الموسّعة من JSON، وإلا يستخدم القائمة الأساسية."""
    if _JSON_PATH.exists():
        try:
            data = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return _BASE_SEED


FOOD_SEED: list[dict] = _load_seed()
