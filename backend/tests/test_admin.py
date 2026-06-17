"""اختبارات لوحة الإشراف (سوبر أدمن) — التحكّم في الصلاحيات وإدارة المستخدمين."""
from sqlalchemy import select

from app.models.user import User
from tests.conftest import auth_headers


def _promote(db, username: str):
    u = db.scalar(select(User).where(User.username == username))
    u.is_admin = True
    db.commit()
    return u


def test_admin_endpoints_require_auth(client):
    assert client.get("/admin/users").status_code == 401
    assert client.get("/admin/users/1").status_code == 401


def test_non_admin_forbidden(client):
    h = auth_headers(client, "normaluser", "pass1234")
    assert client.get("/admin/users", headers=h).status_code == 403
    assert client.get("/admin/users/1", headers=h).status_code == 403
    assert client.post("/admin/users/1/reset-password", json={"new_password": "xxxxxx"}, headers=h).status_code == 403
    assert client.delete("/admin/users/1", headers=h).status_code == 403


def test_admin_can_list_view_reset_promote_delete(client, db_session):
    # مستخدم عادي هدف + مشرف
    auth_headers(client, "target1", "targetpass")
    ah = auth_headers(client, "boss", "bosspass1")
    _promote(db_session, "boss")

    # قائمة المستخدمين
    r = client.get("/admin/users", headers=ah)
    assert r.status_code == 200
    users = r.json()
    assert any(u["username"] == "target1" for u in users)
    tid = next(u["id"] for u in users if u["username"] == "target1")

    # تفاصيل المستخدم
    r = client.get(f"/admin/users/{tid}", headers=ah)
    assert r.status_code == 200
    assert r.json()["username"] == "target1"

    # تعيين كلمة سر جديدة
    r = client.post(f"/admin/users/{tid}/reset-password", json={"new_password": "newpass123"}, headers=ah)
    assert r.status_code == 200
    assert client.post("/auth/login", json={"username": "target1", "password": "newpass123"}).status_code == 200
    assert client.post("/auth/login", json={"username": "target1", "password": "targetpass"}).status_code == 401

    # منح صلاحية الإشراف
    r = client.post(f"/admin/users/{tid}/admin", json={"is_admin": True}, headers=ah)
    assert r.status_code == 200
    assert client.get("/admin/users", headers={"Authorization": f"Bearer {client.post('/auth/login', json={'username':'target1','password':'newpass123'}).json()['access_token']}"}).status_code == 200

    # حذف المستخدم
    r = client.delete(f"/admin/users/{tid}", headers=ah)
    assert r.status_code == 200
    assert client.get(f"/admin/users/{tid}", headers=ah).status_code == 404


def test_admin_cannot_delete_or_demote_self(client, db_session):
    ah = auth_headers(client, "boss2", "bosspass1")
    boss = _promote(db_session, "boss2")
    bid = boss.id
    assert client.delete(f"/admin/users/{bid}", headers=ah).status_code == 400
    assert client.post(f"/admin/users/{bid}/admin", json={"is_admin": False}, headers=ah).status_code == 400


def test_me_reports_is_admin(client, db_session):
    ah = auth_headers(client, "boss3", "bosspass1")
    # قبل الترقية
    assert client.get("/auth/me", headers=ah).json()["is_admin"] is False
    _promote(db_session, "boss3")
    assert client.get("/auth/me", headers=ah).json()["is_admin"] is True
