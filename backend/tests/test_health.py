"""اختبارات مزامنة الصحة (هواوي/Health Connect/يدوي)."""
from datetime import date

from tests.conftest import auth_headers, make_premium

PROFILE = {
    "age": 30, "sex": "male", "height_cm": 180, "weight_kg": 90,
    "activity_level": "moderate", "goal_weight_kg": 78, "goal_rate": 0.5,
}
TODAY = date.today().isoformat()


def test_health_status(client):
    h = auth_headers(client, "hsy1")
    r = client.get("/health/status", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["huawei_configured"] is False  # غير مُهيّأ في التطوير
    assert "هواوي الصحة" in body["providers_priority_ar"][0]


def test_huawei_authorize_not_configured(client):
    h = auth_headers(client, "hsy2")
    r = client.get("/health/huawei/authorize", headers=h)
    assert r.status_code == 503  # غير مُهيّأ


def test_sync_stores_activity_and_sleep(client, db_session):
    h = auth_headers(client, "hsy3")
    make_premium(db_session, "hsy3")  # مزامنة الصحة ميزة مدفوعة
    payload = {"date": TODAY, "source": "huawei", "steps": 8000,
               "active_minutes": 45, "calories_burned": 300, "sleep_hours": 7.5}
    r = client.post("/health/sync", json=payload, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["saved_activity"] and body["saved_sleep"]

    # النشاط ظهر في /health/data و /activity
    r = client.get(f"/health/data?on={TODAY}", headers=h)
    assert len(r.json()) == 1
    assert r.json()[0]["steps"] == 8000
    assert r.json()[0]["source"] == "huawei"

    # النوم اتسجّل في المزاج
    r = client.get(f"/mood?on={TODAY}", headers=h)
    assert r.json()["sleep_hours"] == 7.5


def test_sync_calories_not_deducted_from_food_budget(client, db_session):
    h = auth_headers(client, "hsy4")
    make_premium(db_session, "hsy4")
    client.put("/profile", json=PROFILE, headers=h)
    client.post("/health/sync", json={"date": TODAY, "source": "health_connect",
                                      "calories_burned": 500, "steps": 10000}, headers=h)
    # الملخص: المتاكل لسه صفر (النشاط ما اتخصمش ولا اتضاف لميزانية الأكل)
    r = client.get(f"/summary?on={TODAY}", headers=h)
    assert r.json()["eaten_calories"] == 0
    assert r.json()["activity_note_ar"]


def test_sync_requires_auth(client):
    r = client.post("/health/sync", json={"steps": 100})
    assert r.status_code == 401


def test_sync_blocked_for_free_user(client):
    h = auth_headers(client, "hsyfree")
    r = client.post("/health/sync", json={"date": TODAY, "source": "huawei", "steps": 100}, headers=h)
    assert r.status_code == 402  # ميزة مدفوعة
