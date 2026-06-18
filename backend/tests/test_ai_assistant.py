"""اختبارات طبقة المساعد الذكي (Gemini) فوق محلّل الوجبات — مع محاكاة (بدون شبكة)."""
import app.routers.foods as foods_router
from app.config import settings
from tests.conftest import auth_headers


def test_parse_uses_ai_reply_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")  # ai_enabled = True
    monkeypatch.setattr(foods_router.ai_assistant, "meal_reply", lambda *a, **k: "جامد! 💪")
    h = auth_headers(client, "aiuser")
    r = client.post(
        "/foods/parse",
        json={"text": "النهاردة فطرت بيضتين", "default_meal": "breakfast", "confirm": False},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reply_ar"] == "جامد! 💪"
    # السعرات لسه محسوبة محليًا (مش من الـ LLM)
    assert len(body["items"]) >= 1
    assert body["total_calories"] > 0


def test_parse_falls_back_to_heuristic_without_key(client):
    # الافتراضي: مفيش مفتاح → رد محلي عادي (السلوك القديم)
    h = auth_headers(client, "aiuser2")
    r = client.post(
        "/foods/parse",
        json={"text": "النهاردة فطرت بيضتين", "default_meal": "breakfast", "confirm": False},
        headers=h,
    )
    assert r.status_code == 200
    assert body_reply(r) and body_reply(r) != "جامد! 💪"


def test_general_question_uses_assistant(client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(foods_router.ai_assistant, "general_reply", lambda t: "اشرب مية كفاية 💧")
    monkeypatch.setattr(foods_router.ai_assistant, "meal_reply", lambda *a, **k: "AI-meal")
    h = auth_headers(client, "aiuser3")
    r = client.post(
        "/foods/parse",
        json={"text": "ازيك عامل ايه", "default_meal": "snack", "confirm": False},
        headers=h,
    )
    assert r.status_code == 200
    # لو المحلّل مفهمش أكل (مفيش أصناف) → رد المساعد العام
    if not r.json()["items"]:
        assert r.json()["reply_ar"] == "اشرب مية كفاية 💧"


def body_reply(r) -> str:
    return r.json()["reply_ar"]
