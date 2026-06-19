"""اختبارات التفضيلات الغذائية + الحساسية (حفظها واحترام المساعد الذكي لها)."""
import app.routers.assistant as assistant_router
from app.config import settings
from tests.conftest import auth_headers

_PROFILE = {
    "age": 30, "sex": "male", "height_cm": 175, "weight_kg": 80,
    "activity_level": "moderate",
}


def test_profile_persists_dietary_pref_and_allergies(client):
    h = auth_headers(client, "diet_user")
    r = client.put("/profile", json={**_PROFILE, "dietary_pref": "halal", "allergies": "مكسرات، لاكتوز"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dietary_pref"] == "halal"
    assert body["allergies"] == "مكسرات، لاكتوز"
    # GET يرجّعها برضه
    g = client.get("/profile", headers=h).json()
    assert g["dietary_pref"] == "halal"
    assert g["allergies"] == "مكسرات، لاكتوز"


def test_profile_defaults_dietary_pref_none(client):
    h = auth_headers(client, "diet_default")
    r = client.put("/profile", json=_PROFILE, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["dietary_pref"] == "none"
    assert r.json()["allergies"] is None


def test_profile_rejects_invalid_dietary_pref(client):
    h = auth_headers(client, "diet_bad")
    r = client.put("/profile", json={**_PROFILE, "dietary_pref": "carnivore"}, headers=h)
    assert r.status_code == 422  # Literal يرفض القيمة


def test_assistant_context_includes_diet_and_allergies(client, monkeypatch):
    captured: dict = {}

    def fake_chat_reply(messages, system_extra=None):
        captured["system_extra"] = system_extra
        return "تمام 👍"

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(assistant_router.ai_assistant, "chat_reply", fake_chat_reply)
    h = auth_headers(client, "diet_ai")
    client.put("/profile", json={**_PROFILE, "dietary_pref": "vegan", "allergies": "فول سوداني"}, headers=h)

    r = client.post("/assistant/chat", json={"messages": [{"role": "user", "content": "اقترحلي عشا"}]}, headers=h)
    assert r.status_code == 200, r.text
    ctx = captured["system_extra"] or ""
    assert "فيجان" in ctx or "نباتي" in ctx
    assert "فول سوداني" in ctx
