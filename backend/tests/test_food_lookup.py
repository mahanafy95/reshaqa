"""اختبارات البحث الغذائي الخارجي (سلسلة الذكاء الاصطناعي المجانية + OpenFoodFacts) — بمحاكاة، بلا شبكة."""
import httpx

import app.services.ai_assistant as ai
import app.services.food_lookup as fl
from app.config import settings


class _Resp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def _enable(monkeypatch):
    monkeypatch.setattr(settings, "FOOD_LOOKUP_ENABLED", True)


def _no_ai(monkeypatch):
    """يخلّي سلسلة الذكاء ترجّع None (نختبر OFF لوحده)."""
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: None)


def test_disabled_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "FOOD_LOOKUP_ENABLED", False)
    assert fl.search_food_calories("أي حاجة") is None


def test_openfoodfacts_hit_when_ai_none(monkeypatch):
    _enable(monkeypatch)
    _no_ai(monkeypatch)  # الذكاء فشل → نرجع لـ OFF
    payload = {"products": [
        {"product_name": "Hazelnut Choc", "nutriments": {
            "energy-kcal_100g": 255, "proteins_100g": 8, "carbohydrates_100g": 52, "fat_100g": 35}},
    ]}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(200, payload))
    r = fl.search_food_calories("شوكولاتة بالبندق")
    assert r is not None and r.source == "openfoodfacts"
    assert r.kcal_per_100 == 255 and r.protein == 8


def test_off_energy_kj_fallback(monkeypatch):
    _enable(monkeypatch)
    _no_ai(monkeypatch)
    payload = {"products": [{"product_name": "X", "nutriments": {"energy_100g": 1000}}]}  # kJ -> ~239 kcal
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(200, payload))
    r = fl.search_food_calories("منتج")
    assert r is not None and 230 <= r.kcal_per_100 <= 245


def test_extract_kcal_avoids_the_100g_number():
    # «في 100 جرام يوجد 130 سعرة» → لازم يطلّع 130 مش 100
    assert fl._extract_kcal("في 100 جرام يوجد 130 سعرة حرارية") == 130
    assert fl._extract_kcal("الكشري حوالي 150 سعرة لكل 100 جرام") == 150
    assert fl._extract_kcal("about 89 kcal per 100 g") == 89
    assert fl._extract_kcal("مفيش أرقام هنا") is None


def test_ai_answers_food_calories(monkeypatch):
    """سلسلة الذكاء بترد بجملة فيها السعرات → نطلّع الرقم ومصدره 'ai' (الـ AI أولاً قبل OFF)."""
    _enable(monkeypatch)
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: "حوالي 130 سعرة حرارية لكل 100 جرام")
    # حتى لو OFF رجّع رقم خرافي، الـ AI بيُسأل أولاً
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(200, {"products": [
        {"product_name": "bad", "nutriments": {"energy-kcal_100g": 99999}}]}))
    r = fl.search_food_calories("أكلة غريبة")
    assert r is not None and r.source == "ai" and r.kcal_per_100 == 130


def test_ai_garbage_then_off(monkeypatch):
    """لو الذكاء رد بنص من غير رقم سعرات → نرجع لـ OFF."""
    _enable(monkeypatch)
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: "مش عارف الأكلة دي")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(200, {"products": [
        {"product_name": "Real", "nutriments": {"energy-kcal_100g": 200}}]}))
    r = fl.search_food_calories("حاجة")
    assert r is not None and r.source == "openfoodfacts" and r.kcal_per_100 == 200


def test_ai_and_off_both_miss_returns_none(monkeypatch):
    _enable(monkeypatch)
    _no_ai(monkeypatch)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(200, {"products": []}))  # OFF miss
    assert fl.search_food_calories("حاجة") is None


def test_network_error_is_quiet(monkeypatch):
    _enable(monkeypatch)
    _no_ai(monkeypatch)

    def boom(*a, **k):
        raise httpx.ConnectError("no net")

    monkeypatch.setattr(httpx, "get", boom)
    assert fl.search_food_calories("أكلة") is None  # يتعطّل بهدوء


def test_short_name_skipped(monkeypatch):
    _enable(monkeypatch)
    called = {"n": 0}

    def fake_get(*a, **k):
        called["n"] += 1
        return _Resp(200, {"products": []})

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(ai, "ai_complete", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not call")))
    assert fl.search_food_calories("ا") is None  # أقصر من حرفين → مفيش نداء
    assert called["n"] == 0
