"""اختبارات الاشتراكات (Google Play Billing) — مع محاكاة تحقّق Play (بدون شبكة)."""
from datetime import datetime, timedelta, timezone

import app.routers.billing as billing_router
from app.services.play_billing import PlaySubscription
from tests.conftest import auth_headers, make_premium

PROFILE = {"age": 30, "sex": "male", "height_cm": 180, "weight_kg": 90, "activity_level": "moderate"}
RECIPE = {
    "name_ar": "وصفة", "servings": 1,
    "ingredients": [{"name_ar": "أرز", "amount_g": 100, "per100_calories": 130,
                     "per100_protein": 2.7, "per100_carbs": 28, "per100_fat": 0.3}],
}


def _mock_play(monkeypatch, *, status="active", days=30, acknowledged=False, product="reshaqa_premium"):
    expiry = datetime.now(timezone.utc) + timedelta(days=days)
    sub = PlaySubscription(status=status, product_id=product, expiry=expiry,
                           auto_renewing=True, acknowledged=acknowledged)
    monkeypatch.setattr(billing_router.play_billing, "verify_purchase", lambda t: sub)
    monkeypatch.setattr(billing_router.play_billing, "acknowledge_purchase", lambda t: True)


def test_status_default_not_premium(client):
    h = auth_headers(client, "bill1")
    r = client.get("/billing/status", headers=h).json()
    assert r["is_premium"] is False and r["status"] == "none"


def test_verify_activates_premium_end_to_end(client, monkeypatch):
    _mock_play(monkeypatch)
    h = auth_headers(client, "bill2")
    r = client.post("/billing/google/verify",
                    json={"product_id": "reshaqa_premium", "purchase_token": "tok-2"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["is_premium"] is True
    # /auth/me يعكس Premium
    assert client.get("/auth/me", headers=h).json()["is_premium"] is True
    # وميزة مدفوعة (التقارير) بقت متاحة
    client.put("/profile", json=PROFILE, headers=h)
    assert client.get("/reports/weekly", headers=h).status_code == 200


def test_verify_invalid_token_returns_400(client, monkeypatch):
    monkeypatch.setattr(billing_router.play_billing, "verify_purchase", lambda t: None)
    h = auth_headers(client, "bill3")
    r = client.post("/billing/google/verify",
                    json={"product_id": "reshaqa_premium", "purchase_token": "bad"}, headers=h)
    assert r.status_code == 400


def test_verify_token_bound_to_other_user_409(client, monkeypatch):
    _mock_play(monkeypatch)
    h1 = auth_headers(client, "bill4")
    client.post("/billing/google/verify",
                json={"product_id": "reshaqa_premium", "purchase_token": "shared"}, headers=h1)
    h2 = auth_headers(client, "bill5")
    r = client.post("/billing/google/verify",
                    json={"product_id": "reshaqa_premium", "purchase_token": "shared"}, headers=h2)
    assert r.status_code == 409


def test_expired_subscription_not_premium(client, monkeypatch):
    _mock_play(monkeypatch, status="active", days=-1, acknowledged=True)  # انتهت فترتها
    h = auth_headers(client, "bill6")
    r = client.post("/billing/google/verify",
                    json={"product_id": "reshaqa_premium", "purchase_token": "exp"}, headers=h)
    assert r.status_code == 200
    assert r.json()["is_premium"] is False


def test_canceled_but_not_expired_still_premium(client, monkeypatch):
    # ملغى تلقائي التجديد لكن لسه ضمن الفترة المدفوعة => Premium (in_grace أو active)
    _mock_play(monkeypatch, status="in_grace_period", days=3)
    h = auth_headers(client, "bill7")
    r = client.post("/billing/google/verify",
                    json={"product_id": "reshaqa_premium", "purchase_token": "grace"}, headers=h)
    assert r.json()["is_premium"] is True


def test_recipe_free_limit_then_premium_unlimited(client, monkeypatch, db_session):
    h = auth_headers(client, "recfree")
    for _ in range(3):  # FREE_RECIPE_LIMIT = 3
        assert client.post("/recipes", json=RECIPE, headers=h).status_code == 201
    # الرابعة مرفوضة للمجاني
    blocked = client.post("/recipes", json=RECIPE, headers=h)
    assert blocked.status_code == 402
    assert blocked.json()["detail"]["premium_required"] is True
    # بعد الترقية => بلا حدود
    make_premium(db_session, "recfree")
    assert client.post("/recipes", json=RECIPE, headers=h).status_code == 201


def test_admin_grant_and_revoke_premium(client, db_session):
    from sqlalchemy import select
    from app.models.user import User

    th = auth_headers(client, "giftme", "pass1234")
    ah = auth_headers(client, "bossgift", "bosspass1")
    u = db_session.scalar(select(User).where(User.username == "bossgift"))
    u.is_admin = True
    db_session.commit()
    tid = next(x["id"] for x in client.get("/admin/users", headers=ah).json() if x["username"] == "giftme")

    # قبل المنح: مجاني
    assert client.get("/auth/me", headers=th).json()["is_premium"] is False
    # منح Premium مجاناً (بدون دفع)
    r = client.post(f"/admin/users/{tid}/premium", json={"grant": True, "days": 30}, headers=ah)
    assert r.status_code == 200, r.text
    assert client.get("/auth/me", headers=th).json()["is_premium"] is True
    # وميزة مدفوعة بقت متاحة من غير ما يدفع
    client.put("/profile", json={"age": 30, "sex": "male", "height_cm": 180, "weight_kg": 90, "activity_level": "moderate"}, headers=th)
    assert client.get("/reports/weekly", headers=th).status_code == 200
    # سحب Premium
    assert client.post(f"/admin/users/{tid}/premium", json={"grant": False}, headers=ah).status_code == 200
    assert client.get("/auth/me", headers=th).json()["is_premium"] is False


def test_grant_premium_forever(client, db_session):
    from sqlalchemy import select
    from app.models.user import User

    th = auth_headers(client, "forever", "pass1234")
    ah = auth_headers(client, "boss4ever", "bosspass1")
    u = db_session.scalar(select(User).where(User.username == "boss4ever"))
    u.is_admin = True
    db_session.commit()
    tid = next(x["id"] for x in client.get("/admin/users", headers=ah).json() if x["username"] == "forever")
    # منح بلا انتهاء (days=None)
    client.post(f"/admin/users/{tid}/premium", json={"grant": True}, headers=ah)
    assert client.get("/auth/me", headers=th).json()["is_premium"] is True


def test_non_admin_cannot_grant_premium(client):
    h = auth_headers(client, "sneaky")
    assert client.post("/admin/users/1/premium", json={"grant": True}, headers=h).status_code == 403


def test_barcode_blocked_for_free_user(client):
    h = auth_headers(client, "bcfree")
    r = client.get("/billing/status", headers=h)  # sanity
    assert r.status_code == 200
    rb = client.get("/foods/barcode/6221031492015", headers=h)
    assert rb.status_code == 402  # ميزة مدفوعة (التحقّق قبل أي نداء خارجي)
