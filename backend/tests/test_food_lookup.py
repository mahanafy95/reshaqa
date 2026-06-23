"""اختبارات البحث الغذائي الخارجي (OpenFoodFacts + Gemini grounding) — بمحاكاة httpx، بلا شبكة."""
import httpx

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


def test_disabled_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "FOOD_LOOKUP_ENABLED", False)
    assert fl.search_food_calories("أي حاجة") is None


def test_openfoodfacts_hit_when_no_gemini(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")  # Gemini متخطّى → OFF
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
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
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


def test_gemini_answers_food_calories(monkeypatch):
    """مفتاح Gemini موجود → يُسأل أولاً ويرجّع رقم السعرات (نداء عادي، بدون بحث Google)."""
    _enable(monkeypatch)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "g-key")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(200, {"products": [
        {"product_name": "bad", "nutriments": {"energy-kcal_100g": 99999}}]}))
    gem = {"candidates": [{"content": {"parts": [{"text": "حوالي 130 سعرة حرارية لكل 100 جرام"}]}}]}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(200, gem))
    r = fl.search_food_calories("أكلة غريبة")
    assert r is not None and r.source == "gemini" and r.kcal_per_100 == 130


def test_gemini_omits_paid_search_tool_by_default(monkeypatch):
    """افتراضيًا (GEMINI_GROUNDING_ENABLED=False) منبعتش أداة بحث Google المدفوعة — نداء عادي مجاني."""
    _enable(monkeypatch)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "g-key")
    monkeypatch.setattr(settings, "GEMINI_GROUNDING_ENABLED", False)
    captured = {}

    def cap_post(*a, **k):
        captured["json"] = k.get("json")
        return _Resp(200, {"candidates": [{"content": {"parts": [{"text": "120 سعرة لكل 100 جرام"}]}}]})

    monkeypatch.setattr(httpx, "post", cap_post)
    r = fl.search_food_calories("حاجة جديدة")
    assert r is not None and r.kcal_per_100 == 120
    assert "tools" not in (captured.get("json") or {})


def test_gemini_skipped_without_key(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(200, {"products": []}))  # OFF miss
    assert fl.search_food_calories("حاجة") is None


def test_network_error_is_quiet(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

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
    assert fl.search_food_calories("ا") is None  # أقصر من حرفين → مفيش نداء
    assert called["n"] == 0
