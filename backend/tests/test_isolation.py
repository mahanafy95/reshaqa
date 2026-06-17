"""اختبارات عزل بيانات المستخدمين — حرجة للأمان."""
from tests.conftest import auth_headers

PROFILE_A = {
    "age": 35, "sex": "female", "height_cm": 165, "weight_kg": 80,
    "activity_level": "light", "goal_weight_kg": 65, "goal_rate": 0.5,
}
PROFILE_B = {
    "age": 28, "sex": "male", "height_cm": 175, "weight_kg": 95,
    "activity_level": "active", "goal_weight_kg": 80, "goal_rate": 0.6,
}


def test_users_do_not_see_each_others_profile(client):
    ha = auth_headers(client, "alice")
    hb = auth_headers(client, "bob")

    client.put("/profile", json=PROFILE_A, headers=ha)
    # bob لم يُنشئ ملفاً => يجب أن يحصل على 404 (لا يرى ملف alice)
    rb = client.get("/profile", headers=hb)
    assert rb.status_code == 404


def test_targets_isolated_per_user(client):
    ha = auth_headers(client, "carol")
    hb = auth_headers(client, "dave")

    client.put("/profile", json=PROFILE_A, headers=ha)
    client.put("/profile", json=PROFILE_B, headers=hb)

    ra = client.get("/targets", headers=ha).json()
    rb = client.get("/targets", headers=hb).json()

    # كل مستخدم يرى وزنه هو فقط
    assert ra["current_weight_kg"] == 80
    assert rb["current_weight_kg"] == 95
    assert ra["bmr"] != rb["bmr"]  # حسابات مختلفة تماماً لكل مستخدم


def test_today_target_isolated(client):
    ha = auth_headers(client, "erin")
    hb = auth_headers(client, "frank")
    client.put("/profile", json=PROFILE_A, headers=ha)
    client.put("/profile", json=PROFILE_B, headers=hb)

    ta = client.post("/targets/today", headers=ha).json()
    tb = client.post("/targets/today", headers=hb).json()
    assert ta["calories"] != tb["calories"]
