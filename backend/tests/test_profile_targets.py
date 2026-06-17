"""اختبارات الملف الشخصي والأهداف."""
from tests.conftest import auth_headers

PROFILE = {
    "age": 30,
    "sex": "male",
    "height_cm": 180,
    "weight_kg": 90,
    "activity_level": "moderate",
    "goal_weight_kg": 78,
    "goal_rate": 0.5,
}


def test_upsert_and_get_profile(client):
    h = auth_headers(client, "user1")
    r = client.put("/profile", json=PROFILE, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["healthy_min_kg"] > 0 and body["healthy_max_kg"] > body["healthy_min_kg"]

    r2 = client.get("/profile", headers=h)
    assert r2.status_code == 200
    assert r2.json()["weight_kg"] == 90


def test_profile_required_before_targets(client):
    h = auth_headers(client, "user2")
    r = client.get("/targets", headers=h)
    assert r.status_code == 400


def test_goal_weight_below_healthy_blocked(client):
    h = auth_headers(client, "user3")
    bad = {**PROFILE, "height_cm": 170, "goal_weight_kg": 48}
    r = client.put("/profile", json=bad, headers=h)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["suggested_goal_kg"] == detail["healthy_min_kg"]


def test_targets_computed_loss_mode(client):
    h = auth_headers(client, "user4")
    client.put("/profile", json=PROFILE, headers=h)
    r = client.get("/targets", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "loss"
    assert body["target_calories"] >= 1500
    assert body["macros"]["protein_g"] > 0
    assert body["current_weight_kg"] == 90


def test_maintain_mode_when_at_goal(client):
    h = auth_headers(client, "user5")
    at_goal = {**PROFILE, "weight_kg": 78, "goal_weight_kg": 78}
    client.put("/profile", json=at_goal, headers=h)
    r = client.get("/targets", headers=h)
    assert r.json()["mode"] == "maintain"
    assert r.json()["deficit_applied"] == 0


def test_save_today_target_persists(client):
    h = auth_headers(client, "user6")
    client.put("/profile", json=PROFILE, headers=h)
    r = client.post("/targets/today", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["calories"] >= 1500
    assert body["mode"] == "loss"
    # حفظ ثانٍ يحدّث نفس اليوم (لا يكرّر)
    r2 = client.post("/targets/today", headers=h)
    assert r2.status_code == 200
