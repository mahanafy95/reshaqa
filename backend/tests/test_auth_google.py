"""اختبارات تسجيل الدخول بجوجل — مع محاكاة التحقّق من الرمز (بدون شبكة)."""
import app.routers.auth as auth_router
from app.config import settings


def _enable_google(monkeypatch, info):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_IDS", "test-web-client.apps.googleusercontent.com")
    monkeypatch.setattr(auth_router, "verify_google_id_token", lambda _t: info)


def test_auth_config_reflects_settings(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_IDS", "")
    c = client.get("/auth/config").json()
    assert c["google_login_enabled"] is False
    assert c["google_client_id"] == ""

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_IDS", "abc.apps.googleusercontent.com")
    c = client.get("/auth/config").json()
    assert c["google_login_enabled"] is True
    assert c["google_client_id"] == "abc.apps.googleusercontent.com"


def test_google_disabled_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_IDS", "")
    r = client.post("/auth/google", json={"id_token": "x" * 20})
    assert r.status_code == 503


def test_google_invalid_token(client, monkeypatch):
    _enable_google(monkeypatch, None)
    r = client.post("/auth/google", json={"id_token": "x" * 20})
    assert r.status_code == 401


def test_google_creates_new_user_and_me(client, monkeypatch):
    info = {"email": "sara@gmail.com", "sub": "g-111", "name": "Sara", "email_verified": True}
    _enable_google(monkeypatch, info)
    r = client.post("/auth/google", json={"id_token": "x" * 20})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["email"] == "sara@gmail.com"
    assert me["username"].startswith("sara")


def test_google_login_is_idempotent(client, monkeypatch):
    info = {"email": "omar@gmail.com", "sub": "g-222", "name": "Omar", "email_verified": True}
    _enable_google(monkeypatch, info)
    id1 = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {client.post('/auth/google', json={'id_token': 'x'*20}).json()['access_token']}"},
    ).json()["id"]
    id2 = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {client.post('/auth/google', json={'id_token': 'x'*20}).json()['access_token']}"},
    ).json()["id"]
    assert id1 == id2  # نفس الحساب، مش حساب جديد


def test_google_links_to_existing_email_account(client, monkeypatch):
    # مستخدم سجّل بكلمة سر وبريد
    r = client.post(
        "/auth/register",
        json={"username": "laila", "password": "pass1234", "email": "laila@gmail.com"},
    )
    assert r.status_code == 201
    uid = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}
    ).json()["id"]

    info = {"email": "laila@gmail.com", "sub": "g-333", "name": "Laila", "email_verified": True}
    _enable_google(monkeypatch, info)
    g = client.post("/auth/google", json={"id_token": "x" * 20})
    assert g.status_code == 200
    gid = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {g.json()['access_token']}"}
    ).json()["id"]
    assert gid == uid  # اترَبط بنفس الحساب


def test_google_only_user_cannot_password_login(client, monkeypatch):
    info = {"email": "noor@gmail.com", "sub": "g-444", "name": "Noor", "email_verified": True}
    _enable_google(monkeypatch, info)
    token = client.post("/auth/google", json={"id_token": "x" * 20}).json()["access_token"]
    username = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["username"]
    # محاولة دخول بكلمة سر لحساب جوجل-فقط لازم تفشل
    r = client.post("/auth/login", json={"username": username, "password": "anything"})
    assert r.status_code == 401
