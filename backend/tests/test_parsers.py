"""اختبارات المحلّلات النقية: المُقدِّر، الباركود، وملصق التغذية."""
import pytest

from app.services.barcode import parse_off_product
from app.services.estimator import HeuristicEstimator
from app.services.ocr import parse_nutrition_text


def _approx(v):
    return pytest.approx(v, rel=0.02)


# ---------- المُقدِّر ----------
def test_estimator_oil_is_high_fat():
    e = HeuristicEstimator().estimate("زيت زيتون", 100)
    assert e.calories > 800
    assert e.fat > 90


def test_estimator_grilled_chicken_high_protein():
    e = HeuristicEstimator().estimate("صدر فراخ مشوي", 100)
    assert e.protein >= 20


def test_estimator_scales_with_amount():
    e50 = HeuristicEstimator().estimate("رز", 50)
    e100 = HeuristicEstimator().estimate("رز", 100)
    assert e100.calories == _approx(e50.calories * 2)


def test_estimator_unknown_food_returns_default():
    e = HeuristicEstimator().estimate("أكلة غريبة مش معروفة", 100)
    assert e.calories > 0
    assert e.confidence in ("low", "medium")


# ---------- الباركود (Open Food Facts) ----------
def test_parse_off_product_kcal():
    payload = {
        "status": 1,
        "product": {
            "product_name": "Sample Bar",
            "nutriments": {
                "energy-kcal_100g": 450,
                "proteins_100g": 8,
                "carbohydrates_100g": 60,
                "fat_100g": 20,
            },
        },
    }
    r = parse_off_product(payload, "12345")
    assert r is not None
    assert r.calories_per_100 == 450
    assert r.protein == 8


def test_parse_off_product_not_found():
    assert parse_off_product({"status": 0}, "0000") is None


def test_parse_off_product_energy_kj_fallback():
    payload = {"status": 1, "product": {"nutriments": {"energy_100g": 2000}}}
    r = parse_off_product(payload, "999")
    assert r is not None
    assert 470 < r.calories_per_100 < 480  # 2000 kJ ≈ 478 kcal


# ---------- ملصق التغذية ----------
def test_parse_label_arabic():
    text = "القيمة الغذائية لكل 100 جرام\nالسعرات الحرارية 250\nبروتين 12\nكربوهيدرات 30\nدهون 9"
    ex = parse_nutrition_text(text)
    assert ex.calories == 250
    assert ex.protein == 12
    assert ex.carbs == 30
    assert ex.fat == 9
    assert ex.basis_ar == "لكل 100 جرام"


def test_parse_label_english():
    text = "Per serving\nCalories 180 kcal\nProtein 5 g\nCarbohydrate 22 g\nFat 8 g"
    ex = parse_nutrition_text(text)
    assert ex.calories == 180
    assert ex.fat == 8
    assert ex.basis_ar == "لكل حصة"
