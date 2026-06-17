"""اختبارات المتابعة: الوزن/الاتجاه، الوسط، المياه، النشاط، المزاج."""
from datetime import date, timedelta

from tests.conftest import auth_headers

PROFILE = {
    "age": 30, "sex": "male", "height_cm": 180, "weight_kg": 90,
    "activity_level": "moderate", "goal_weight_kg": 78, "goal_rate": 0.5,
}


def test_weight_add_and_same_day_updates(client):
    h = auth_headers(client, "tw1")
    client.post("/weight", json={"date": "2026-06-10", "weight_kg": 90}, headers=h)
    # نفس اليوم يحدّث لا يكرّر
    client.post("/weight", json={"date": "2026-06-10", "weight_kg": 89.5}, headers=h)
    r = client.get("/weight", headers=h)
    assert len(r.json()) == 1
    assert r.json()[0]["weight_kg"] == 89.5


def test_weight_trend_moving_average(client):
    h = auth_headers(client, "tw2")
    start = date(2026, 1, 1)
    for i in range(21):
        d = (start + timedelta(days=i)).isoformat()
        client.post("/weight", json={"date": d, "weight_kg": 90 - i * 0.1}, headers=h)
    r = client.get("/weight/trend", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert len(body["points"]) == 21
    assert body["current_trend_kg"] is not None
    assert body["slope_kg_per_week"] is not None


def test_water_counter_and_goal(client):
    h = auth_headers(client, "tw3")
    client.put("/profile", json=PROFILE, headers=h)  # goal يعتمد على الوزن
    today = date.today().isoformat()
    r = client.post("/water", json={"date": today, "ml": 500}, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["total_ml"] == 500
    assert body["goal_ml"] > 0
    client.post("/water", json={"date": today, "ml": 500}, headers=h)
    r = client.get(f"/water?on={today}", headers=h)
    assert r.json()["total_ml"] == 1000


def test_activity_separate_not_in_food(client):
    h = auth_headers(client, "tw4")
    today = date.today().isoformat()
    r = client.post("/activity", json={"date": today, "type_ar": "مشي", "duration_min": 30, "calories_burned": 150}, headers=h)
    assert r.status_code == 201
    aid = r.json()["id"]
    r = client.get(f"/activity?on={today}", headers=h)
    assert len(r.json()) == 1
    # حذف
    assert client.delete(f"/activity/{aid}", headers=h).status_code == 204


def test_mood_upsert(client):
    h = auth_headers(client, "tw5")
    today = date.today().isoformat()
    r = client.put("/mood", json={"date": today, "energy": 4, "sleep_hours": 7, "hunger": 2}, headers=h)
    assert r.status_code == 200
    assert r.json()["energy"] == 4
    # تحديث
    r = client.put("/mood", json={"date": today, "energy": 5}, headers=h)
    assert r.json()["energy"] == 5
    r = client.get(f"/mood?on={today}", headers=h)
    assert r.json()["energy"] == 5


def test_waist_optional_separate(client):
    h = auth_headers(client, "tw6")
    r = client.post("/waist", json={"waist_cm": 95}, headers=h)
    assert r.status_code == 201
    assert client.get("/waist", headers=h).json()[0]["waist_cm"] == 95
