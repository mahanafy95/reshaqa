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


def test_admin_can_create_user(client, db_session):
    ah = auth_headers(client, "boss4", "bosspass1")
    _promote(db_session, "boss4")
    # إنشاء مستخدم جديد
    r = client.post("/admin/users", json={"username": "newbie", "password": "newbiepass"}, headers=ah)
    assert r.status_code == 201, r.text
    assert r.json()["username"] == "newbie"
    # المستخدم الجديد يقدر يسجّل دخول بكلمة السر المحددة
    assert client.post("/auth/login", json={"username": "newbie", "password": "newbiepass"}).status_code == 200
    # تكرار الاسم -> 409
    r = client.post("/admin/users", json={"username": "newbie", "password": "another"}, headers=ah)
    assert r.status_code == 409


def test_create_user_can_be_admin(client, db_session):
    ah = auth_headers(client, "boss5", "bosspass1")
    _promote(db_session, "boss5")
    r = client.post("/admin/users", json={"username": "subadmin", "password": "subpass1", "is_admin": True}, headers=ah)
    assert r.status_code == 201
    tok = client.post("/auth/login", json={"username": "subadmin", "password": "subpass1"}).json()["access_token"]
    # المستخدم الجديد مشرف فعلاً
    assert client.get("/admin/users", headers={"Authorization": f"Bearer {tok}"}).status_code == 200


def test_non_admin_cannot_create_user(client):
    h = auth_headers(client, "plainuser", "pass1234")
    assert client.post("/admin/users", json={"username": "x123", "password": "y12345"}, headers=h).status_code == 403


def test_admin_can_change_username(client, db_session):
    auth_headers(client, "oldname", "pass1234")
    ah = auth_headers(client, "boss6", "bosspass1")
    _promote(db_session, "boss6")
    tid = next(u["id"] for u in client.get("/admin/users", headers=ah).json() if u["username"] == "oldname")
    r = client.post(f"/admin/users/{tid}/username", json={"new_username": "newname"}, headers=ah)
    assert r.status_code == 200, r.text
    # الدخول بالاسم الجديد يشتغل، والقديم لأ
    assert client.post("/auth/login", json={"username": "newname", "password": "pass1234"}).status_code == 200
    assert client.post("/auth/login", json={"username": "oldname", "password": "pass1234"}).status_code == 401


def test_change_username_conflict(client, db_session):
    auth_headers(client, "taken", "pass1234")
    auth_headers(client, "mover", "pass1234")
    ah = auth_headers(client, "boss7", "bosspass1")
    _promote(db_session, "boss7")
    mid = next(u["id"] for u in client.get("/admin/users", headers=ah).json() if u["username"] == "mover")
    r = client.post(f"/admin/users/{mid}/username", json={"new_username": "taken"}, headers=ah)
    assert r.status_code == 409


def test_bulk_delete_skips_admins_and_self(client, db_session):
    # حسابات تجريبية عادية
    auth_headers(client, "junk1", "pass1234")
    auth_headers(client, "junk2", "pass1234")
    auth_headers(client, "keepadmin", "pass1234")
    ah = auth_headers(client, "boss8", "bosspass1")
    _promote(db_session, "boss8")
    _promote(db_session, "keepadmin")  # مشرف تاني لازم ما يتحذفش

    users = client.get("/admin/users", headers=ah).json()
    ids = {u["username"]: u["id"] for u in users}
    boss_id = ids["boss8"]
    payload_ids = [ids["junk1"], ids["junk2"], ids["keepadmin"], boss_id]

    r = client.post("/admin/users/bulk-delete", json={"ids": payload_ids}, headers=ah)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deleted"] == 2  # junk1, junk2 فقط
    assert body["skipped"] == 2  # keepadmin (مشرف) + boss8 (نفسه)

    after = {u["username"] for u in client.get("/admin/users", headers=ah).json()}
    assert "junk1" not in after and "junk2" not in after
    assert "keepadmin" in after and "boss8" in after


def test_non_admin_cannot_bulk_delete(client):
    h = auth_headers(client, "plain2", "pass1234")
    assert client.post("/admin/users/bulk-delete", json={"ids": [1, 2]}, headers=h).status_code == 403


def test_admin_is_db_flag_only_not_username():
    # تصعيد الصلاحية مقفول: اسم "admin" وحده ما يمنحش إشراف — العمود is_admin بس
    from app.core.admin import is_user_admin
    from app.models.user import User

    assert is_user_admin(User(username="admin", is_admin=False)) is False
    assert is_user_admin(User(username="ADMIN", is_admin=False)) is False
    assert is_user_admin(User(username="anyone", is_admin=True)) is True


def test_me_reports_is_admin(client, db_session):
    ah = auth_headers(client, "boss3", "bosspass1")
    # قبل الترقية
    assert client.get("/auth/me", headers=ah).json()["is_admin"] is False
    _promote(db_session, "boss3")
    assert client.get("/auth/me", headers=ah).json()["is_admin"] is True
