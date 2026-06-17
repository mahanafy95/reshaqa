"""Smoke test ضد قاعدة Postgres الحقيقية (يستخدم get_db الفعلي بدون تبديل)."""
import sys
import uuid

from fastapi.testclient import TestClient

from app.database import SessionLocal, engine
from app.main import app
from app.models.user import User


def main() -> int:
    print(f"engine: {engine.url}")
    uname = "smoke_" + uuid.uuid4().hex[:8]
    pwd = "smoke12345"
    with TestClient(app) as c:
        r = c.post("/auth/register", json={"username": uname, "password": pwd})
        assert r.status_code == 201, r.text
        token = r.json()["access_token"]
        print("register OK")

        r = c.post("/auth/login", json={"username": uname, "password": pwd})
        assert r.status_code == 200, r.text
        print("login OK")

        r = c.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        assert r.json()["username"] == uname
        print("me OK:", r.json())

        # رفض التكرار
        r = c.post("/auth/register", json={"username": uname, "password": pwd})
        assert r.status_code == 409, r.text
        print("duplicate rejected OK")

    # تنظيف: حذف مستخدم الاختبار
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == uname).first()
        if u:
            db.delete(u)
            db.commit()
            print("cleanup OK")
    finally:
        db.close()

    print("ALL SMOKE CHECKS PASSED (Postgres)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
