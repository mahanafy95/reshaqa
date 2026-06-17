"""اختبارات الملخص اليومي ومؤشرات الجسم والمشروبات."""
from datetime import date

from tests.conftest import auth_headers

PROFILE = {
    "age": 30, "sex": "male", "height_cm": 180, "weight_kg": 90,
    "activity_level": "moderate", "goal_weight_kg": 78, "goal_rate": 0.5,
}
TODAY = date.today().isoformat()


def _log(client, h, cals, p=0, c=0, f=0, meal="lunch"):
    client.post("/foods", json={"date": TODAY, "meal": meal, "name_ar": "أكل",
                                "amount": 100, "calories": cals, "protein": p, "carbs": c, "fat": f}, headers=h)


def test_summary_eaten_and_remaining(client):
    h = auth_headers(client, "su1")
    client.put("/profile", json=PROFILE, headers=h)
    _log(client, h, 500, p=30, c=50, f=15)
    r = client.get(f"/summary?on={TODAY}", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["eaten_calories"] == 500
    assert body["remaining_calories"] == body["target_calories"] - 500
    assert body["calories_status"]["status"] in ("قليل", "مظبوط", "كتير")
    assert body["activity_note_ar"]


def test_summary_over_target_supportive(client):
    h = auth_headers(client, "su2")
    client.put("/profile", json=PROFILE, headers=h)
    # سجّل سعرات كبيرة جداً فوق الهدف
    _log(client, h, 5000)
    r = client.get(f"/summary?on={TODAY}", headers=h)
    body = r.json()
    assert body["calories_status"]["status"] == "كتير"
    # رسالة داعمة بدون لوم
    msg = body["calories_status"]["message_ar"] + body["encouragement_ar"]
    assert "💚" in msg or "بكرة" in msg


def test_body_metrics(client):
    h = auth_headers(client, "su3")
    client.put("/profile", json=PROFILE, headers=h)
    r = client.get("/metrics/body", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bmi"] > 0
    assert body["healthy_min_kg"] < body["healthy_max_kg"]
    assert body["body_fat_pct"] is not None


def test_drinks_suggestions(client):
    h = auth_headers(client, "su4")
    r = client.get("/drinks/suggestions", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 4
    assert any(d["approx_calories"] == 0 for d in r.json())


def test_summary_requires_profile(client):
    h = auth_headers(client, "su5")
    r = client.get("/summary", headers=h)
    assert r.status_code == 400
