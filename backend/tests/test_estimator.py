"""اختبارات مُقدّر السعرات — الإصلاح: الأكلات البسيطة مش بتاخد 160 سعرة افتراضي،
والـ AI (لو مفعّل) بيدّي القيم الواقعية، ومع رجوع آمن للـ heuristic لو الـ AI متعطّل."""
from app.config import settings
from app.services.estimator import (
    HeuristicEstimator,
    _AIEstimator,
    _DEFAULT,
    get_estimator,
)


# ---------- heuristic (بدون AI) ----------
def test_cucumber_not_160_anymore():
    """العطل القديم: «خيارة» كانت بتطلّع 160 سعرة/100جم. دلوقتي خضار ~20."""
    r = HeuristicEstimator().estimate("خيارة", 100)
    assert r.per100_calories < 40
    assert r.calories < 40


def test_common_vegetables_are_low_calorie():
    e = HeuristicEstimator()
    for veg in ("خيار", "طماطم", "جزر", "فلفل", "بصل", "خس", "كوسة"):
        r = e.estimate(veg, 100)
        assert r.per100_calories <= 40, f"{veg} too high: {r.per100_calories}"


def test_common_fruits_are_mid_calorie():
    e = HeuristicEstimator()
    for fruit in ("تفاح", "موز", "برتقال", "فراولة", "عنب"):
        r = e.estimate(fruit, 100)
        assert 30 <= r.per100_calories <= 90, f"{fruit}: {r.per100_calories}"


def test_honey_is_calorie_dense():
    r = HeuristicEstimator().estimate("عسل", 100)
    assert r.per100_calories >= 250


def test_boiled_potato_not_treated_as_boiled_meat():
    """«بطاطس مسلوقة» المفروض ~85 مش 165 (لحم مسلوق)."""
    r = HeuristicEstimator().estimate("بطاطس مسلوقة", 100)
    assert r.per100_calories < 120


def test_unknown_default_lowered_below_old_160():
    r = HeuristicEstimator().estimate("وجبة غريبة جدا مش معروفة", 100)
    assert _DEFAULT[0] < 160
    assert r.per100_calories == _DEFAULT[0]
    assert r.confidence == "low"
    assert r.note_ar  # ملاحظة واضحة تطلب التعديل


def test_amount_scales_calories():
    r = HeuristicEstimator().estimate("خيار", 200)
    assert r.calories == round(r.per100_calories * 2)


# ---------- اختيار المُقدّر حسب الإعدادات ----------
def test_get_estimator_heuristic_without_ai(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    assert isinstance(get_estimator(), HeuristicEstimator)
    assert not isinstance(get_estimator(), _AIEstimator)


def test_get_estimator_ai_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")  # ai_enabled = True
    assert isinstance(get_estimator(), _AIEstimator)


# ---------- مسار الـ AI (مع محاكاة، بدون شبكة) ----------
def test_ai_estimator_uses_ai_values(monkeypatch):
    from app.services import ai_assistant

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        ai_assistant,
        "estimate_calories_ai",
        lambda name, grams: {"kcal_per_100": 15, "protein": 0.7, "carbs": 3.6, "fat": 0.1},
        raising=False,
    )
    r = _AIEstimator().estimate("خيار", 200)
    assert r.per100_calories == 15
    assert r.calories == round(15 * 2)
    assert r.provider == "ai"


def test_ai_estimator_falls_back_when_ai_returns_none(monkeypatch):
    """لو الـ AI رجّع None → نرجع للـ heuristic (لا يفشل التقدير أبداً)."""
    from app.services import ai_assistant

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(ai_assistant, "estimate_calories_ai", lambda name, grams: None, raising=False)
    r = _AIEstimator().estimate("خيار", 100)
    # رجع للـ heuristic → خضار منخفض السعرات (مش افتراضي عالٍ)
    assert r.provider == "heuristic"
    assert r.per100_calories <= 40


def test_ai_estimator_falls_back_when_ai_raises(monkeypatch):
    from app.services import ai_assistant

    def _boom(name, grams):
        raise RuntimeError("network down")

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(ai_assistant, "estimate_calories_ai", _boom, raising=False)
    r = _AIEstimator().estimate("تفاح", 100)
    assert r.provider == "heuristic"
    assert r.calories > 0
