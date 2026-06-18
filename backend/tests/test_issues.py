"""اختبارات بلاغات المشاكل — المستخدم يبلّغ والمشرف يراجع ويحدّث الحالة."""
from sqlalchemy import select

from app.models.user import User
from tests.conftest import auth_headers


def _promote(db, username: str):
    u = db.scalar(select(User).where(User.username == username))
    u.is_admin = True
    db.commit()
    return u


def test_user_can_submit_issue(client):
    h = auth_headers(client, "reporter", "pass1234")
    r = client.post(
        "/issues",
        json={"message": "الشاشة بتقفل فجأة", "context": "home_screen v1.2"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["message"] == "الشاشة بتقفل فجأة"
    assert body["context"] == "home_screen v1.2"
    assert body["status"] == "new"
    assert "id" in body and "created_at" in body


def test_issue_message_too_short_rejected(client):
    h = auth_headers(client, "shorty", "pass1234")
    r = client.post("/issues", json={"message": "x"}, headers=h)
    assert r.status_code == 422


def test_issue_requires_auth(client):
    assert client.post("/issues", json={"message": "مشكلة بدون دخول"}).status_code == 401
    assert client.get("/issues").status_code == 401


def test_non_admin_cannot_list_issues(client):
    h = auth_headers(client, "normal", "pass1234")
    assert client.get("/issues", headers=h).status_code == 403


def test_admin_can_list_and_patch_issues(client, db_session):
    # مستخدم عادي يبعت بلاغ
    hu = auth_headers(client, "user1", "pass1234")
    created = client.post(
        "/issues",
        json={"message": "الإشعارات مش بتيجي", "context": "settings"},
        headers=hu,
    )
    assert created.status_code == 201, created.text
    issue_id = created.json()["id"]

    # مشرف يقدر يشوف القائمة (مع اسم المُبلِّغ)
    ah = auth_headers(client, "boss", "bosspass1")
    _promote(db_session, "boss")
    r = client.get("/issues", headers=ah)
    assert r.status_code == 200
    items = r.json()
    assert any(i["id"] == issue_id for i in items)
    item = next(i for i in items if i["id"] == issue_id)
    assert item["username"] == "user1"
    assert item["status"] == "new"

    # تحديث الحالة → seen
    r = client.patch(f"/issues/{issue_id}", json={"status": "seen"}, headers=ah)
    assert r.status_code == 200
    assert r.json()["status"] == "seen"

    # تحديث الحالة → resolved
    r = client.patch(f"/issues/{issue_id}", json={"status": "resolved"}, headers=ah)
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"


def test_non_admin_cannot_patch_issue(client, db_session):
    hu = auth_headers(client, "user2", "pass1234")
    created = client.post("/issues", json={"message": "مشكلة تانية"}, headers=hu)
    issue_id = created.json()["id"]
    # نفس المستخدم (غير مشرف) ميقدرش يحدّث الحالة
    assert client.patch(f"/issues/{issue_id}", json={"status": "seen"}, headers=hu).status_code == 403


def test_patch_unknown_issue_404(client, db_session):
    ah = auth_headers(client, "boss2", "bosspass1")
    _promote(db_session, "boss2")
    assert client.patch("/issues/999999", json={"status": "seen"}, headers=ah).status_code == 404


def test_invalid_status_rejected(client, db_session):
    hu = auth_headers(client, "user3", "pass1234")
    created = client.post("/issues", json={"message": "مشكلة ثالثة"}, headers=hu)
    issue_id = created.json()["id"]
    ah = auth_headers(client, "boss3", "bosspass1")
    _promote(db_session, "boss3")
    assert client.patch(f"/issues/{issue_id}", json={"status": "closed"}, headers=ah).status_code == 422


def test_issues_ordered_newest_first(client, db_session):
    hu = auth_headers(client, "user4", "pass1234")
    first = client.post("/issues", json={"message": "بلاغ أول قديم"}, headers=hu).json()
    second = client.post("/issues", json={"message": "بلاغ تاني أحدث"}, headers=hu).json()

    ah = auth_headers(client, "boss4", "bosspass1")
    _promote(db_session, "boss4")
    items = client.get("/issues", headers=ah).json()
    ids = [i["id"] for i in items]
    # الأحدث أولاً
    assert ids.index(second["id"]) < ids.index(first["id"])
