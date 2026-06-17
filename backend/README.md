<div dir="rtl">

# Backend — رشاقة

الـ API الرئيسي للتطبيق: المصادقة، قاعدة البيانات، منطق حساب السعرات والماكروز، وكل الـ endpoints.

**التقنية:** FastAPI · PostgreSQL · SQLAlchemy 2.0 · Alembic · JWT · bcrypt

---

## التشغيل المحلي

<div dir="ltr">

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # ويندوز  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy ..\.env.example .env          # ثم عدّل DATABASE_URL و JWT_SECRET_KEY
alembic upgrade head               # إنشاء الجداول
uvicorn app.main:app --reload      # التشغيل على http://localhost:8000
```
</div>

- توثيق تفاعلي: `http://localhost:8000/docs`
- فحص الصحة: `http://localhost:8000/health`

### قاعدة البيانات
- **الإنتاج:** PostgreSQL (مثلاً على Railway) — `DATABASE_URL=postgresql+psycopg://...`
- **محلياً:** Postgres محمول يعمل على المنفذ 5432، قاعدة `reshaqa`. لتشغيله:
  `powershell -ExecutionPolicy Bypass -File scripts\start_postgres.ps1`
- **بديل خفيف:** SQLite — `DATABASE_URL=sqlite:///./reshaqa_dev.db` (الكود يدعم الاثنين تلقائياً).

---

## الاختبارات

<div dir="ltr">

```bash
cd backend
.venv\Scripts\python.exe -m pytest        # اختبارات الوحدة (SQLite في الذاكرة)
.venv\Scripts\python.exe -m scripts.smoke_pg   # smoke test ضد Postgres الحقيقي
```
</div>

---

## البنية

<div dir="ltr">

```
backend/
├── app/
│   ├── main.py            # تطبيق FastAPI + CORS + الراوترات
│   ├── config.py          # الإعدادات من .env
│   ├── database.py        # المحرك والجلسات (Postgres/SQLite)
│   ├── models/            # نماذج ORM (مستخدم، ملف، أهداف، أكل، وصفات، متابعة...)
│   ├── schemas/           # سكيمات Pydantic
│   ├── core/              # الأمان (bcrypt/JWT) والتبعيات
│   ├── routers/           # نقاط النهاية (auth، ...)
│   └── services/          # منطق الأعمال (محرك السعرات...)
├── alembic/               # هجرات قاعدة البيانات
├── tests/                 # اختبارات
└── scripts/               # أدوات مساعدة (تشغيل Postgres، smoke test)
```
</div>

---

## الأمان
- كلمات السر تُجزّأ بـ **bcrypt** (لا تُخزَّن كنص صريح أبداً).
- كل الـ endpoints المحمية تتطلب **JWT** عبر `Authorization: Bearer <token>`.
- كل استعلام يُفلتر بـ `user_id` — عزل كامل لبيانات كل مستخدم.

</div>
