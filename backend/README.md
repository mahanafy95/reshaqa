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

---

## مزامنة الصحة (هواوي / Health Connect)

الأولوية: **هواوي الصحة** → **Android Health Connect** → **إدخال يدوي**.

**المسار الموصى به (يعمل الآن):** يقرأ الموبايل البيانات على الجهاز عبر Huawei Health Kit SDK
أو Health Connect، ثم يدفعها إلى `POST /health/sync`. الخادم يخزّنها كنشاط ونوم.
**السعرات المحروقة للعرض كنشاط فقط ولا تُخصم من ميزانية الأكل.**

**ربط هواوي من جهة الخادم (OAuth):** مُجهّز هيكلياً ويُفعَّل عند ضبط المتغيّرات:
`HUAWEI_HEALTH_CLIENT_ID` و `HUAWEI_HEALTH_CLIENT_SECRET` و `HUAWEI_HEALTH_REDIRECT_URI`.

### خطوات تسجيل مطوّر هواوي (راجع التوثيق الحالي وقت التنفيذ — الـ scopes والموافقات تتغيّر)
1. أنشئ حساباً على [Huawei Developers](https://developer.huawei.com) وفعّل **AppGallery Connect**.
2. أنشئ تطبيقاً واطلب تفعيل **Health Kit** (يتطلب مراجعة وموافقة من هواوي على نوع البيانات).
3. اضبط **OAuth 2.0 Client ID** و **redirect URI** المطابق لـ `HUAWEI_HEALTH_REDIRECT_URI`.
4. اطلب الـ scopes المطلوبة (خطوات/نشاط/نوم) — راجع `app/services/health_sync.py:HUAWEI_DEFAULT_SCOPES`.
5. لازم يكون حساب هواوي هو نفسه المربوط بالساعة، ويوافق المستخدم على مشاركة البيانات.

> ملاحظة: نقاط هواوي والـ scopes في الكود مرجعية؛ تأكّد منها من توثيق Huawei Health Kit الحالي.

</div>
