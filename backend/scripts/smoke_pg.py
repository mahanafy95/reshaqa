"""Smoke test ضد قاعدة Postgres الحقيقية (يستخدم get_db الفعلي بدون تبديل)."""
import sys
import uuid
from datetime import date

# اطبع عربي بأمان على console ويندوز
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

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

        h = {"Authorization": f"Bearer {token}"}
        # ملف شخصي (يكتب enums Sex/ActivityLevel على Postgres مع قيود CHECK)
        prof = {
            "age": 30, "sex": "male", "height_cm": 180, "weight_kg": 90,
            "activity_level": "moderate", "goal_weight_kg": 78, "goal_rate": 0.5,
        }
        r = c.put("/profile", json=prof, headers=h)
        assert r.status_code == 200, r.text
        print("profile upsert OK")

        # منع وزن مستهدف غير صحي
        bad = {**prof, "height_cm": 170, "goal_weight_kg": 48}
        r = c.put("/profile", json=bad, headers=h)
        assert r.status_code == 422, r.text
        print("unsafe goal blocked OK")

        # حساب الأهداف + حفظ هدف اليوم
        r = c.get("/targets", headers=h)
        assert r.status_code == 200 and r.json()["mode"] == "loss", r.text
        r = c.post("/targets/today", headers=h)
        assert r.status_code == 200 and r.json()["calories"] >= 1500, r.text
        print("targets compute + save OK")

        # --- Phase 3: مكتبة + تقدير + تسجيل ---
        r = c.get("/foods/library/search?q=كشري", headers=h)
        assert r.status_code == 200 and len(r.json()) >= 1, r.text
        print(f"library search OK ({len(r.json())} نتيجة)")

        r = c.get("/foods/estimate?name=كشري&amount=350", headers=h)
        assert r.status_code == 200 and r.json()["source"] == "library", r.text
        print("estimate (library) OK")

        today = date.today().isoformat()
        r = c.post("/foods", json={"date": today, "meal": "lunch", "name_ar": "تجربة",
                                   "amount": 100, "calories": 200}, headers=h)
        assert r.status_code == 201, r.text
        r = c.get(f"/foods?on={today}", headers=h)
        assert len(r.json()) == 1
        print("food log OK")

        # وصفة + تسجيل نصيب
        recipe = {"name_ar": "أرز بالزيت", "servings": 2, "ingredients": [
            {"name_ar": "رز", "amount_g": 200, "per100_calories": 130, "per100_protein": 2.7, "per100_carbs": 28, "per100_fat": 0.3},
            {"name_ar": "زيت", "amount_g": 14, "is_oil": True, "per100_calories": 884, "per100_protein": 0, "per100_carbs": 0, "per100_fat": 100},
        ]}
        r = c.post("/recipes", json=recipe, headers=h)
        assert r.status_code == 201, r.text
        rid = r.json()["id"]
        r = c.post(f"/recipes/{rid}/log", json={"date": today, "meal": "dinner", "servings": 1}, headers=h)
        assert r.status_code == 201 and r.json()["source"] == "recipe", r.text
        print("recipe build + portion log OK")

        # مفضّلة
        r = c.post("/favorites", json={"ref_type": "custom", "name_ar": "قهوة", "default_amount": 200, "calories": 5}, headers=h)
        assert r.status_code == 201, r.text
        fid = r.json()["id"]
        r = c.post(f"/favorites/{fid}/log", json={"date": today, "meal": "snack"}, headers=h)
        assert r.status_code == 201, r.text
        print("favorite create + quick log OK")

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
