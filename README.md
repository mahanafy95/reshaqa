<div dir="rtl">

# 🥗 رشاقة — تطبيق حساب السعرات والتغذية للتخسيس الصحي

تطبيق متكامل **متعدد المستخدمين** لحساب السعرات والعناصر الغذائية بهدف **تخسيس صحي وآمن**.
كل الواجهات **عربية بالكامل** واتجاه **RTL**، والنبرة **مشجّعة وداعمة** بدون أي تأنيب أو تعليق على الشكل.

## المكوّنات
| المجلد | الوصف | التقنية | الحالة |
|--------|-------|---------|--------|
| [`/backend`](backend) | API + قاعدة بيانات + منطق الحساب | FastAPI · PostgreSQL · SQLAlchemy · Alembic · JWT | ✅ 96 اختبار |
| [`/mobile`](mobile) | تطبيق أندرويد (APK) | Flutter | ✅ APK جاهز |
| [`/web`](web) | لوحة تحكم الويب | Next.js · Tailwind · RTL | ✅ build ناجح |

---

## 🩺 قواعد الأمان الصحي (مدمجة ومُختبَرة)
- **الاحتياج:** Mifflin-St Jeor × معامل النشاط = TDEE.
- **العجز:** 15–20% أو 500 سعرة (أيهما أقل)، ومعدل نزول أقصاه ~0.75 كجم/أسبوع.
- **حد أدنى آمن:** 1200 سعرة (ستات) / 1500 (رجالة) — لا يقل أبداً.
- **منع الأهداف غير الصحية:** يُمنع وزن مستهدف أقل من BMI 18.5 مع اقتراح أقرب وزن صحي.
- **بوابة أمان:** من وزنه الحالي تحت النطاق الصحي لا يدخل وضع تخسيس إطلاقاً.
- **وضع التثبيت** تلقائياً عند الوصول للهدف.

---

## ▶️ التشغيل المحلي

### المتطلبات
Python 3.12 · PostgreSQL 15+ · Node.js 20+ · Flutter 3.x + Android SDK

### Backend
<div dir="ltr">

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env        # عدّل DATABASE_URL و JWT_SECRET_KEY
alembic upgrade head
python -m scripts.seed_food_library   # تعبئة مكتبة الأكلات (330 صنف)
uvicorn app.main:app --reload         # http://localhost:8000/docs
```
</div>

### Web
<div dir="ltr">

```bash
cd web && npm install
npm run dev                            # http://localhost:3000
```
</div>

### Mobile
<div dir="ltr">

```bash
cd mobile && flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```
</div>

---

## ☁️ النشر

### Backend على Railway
1. على [Railway](https://railway.app): New Project → Deploy، و**Root Directory = `backend`**.
2. أضف **PostgreSQL** plugin (يوفّر `DATABASE_URL` تلقائياً — الكود يطبّعه لـ psycopg3).
3. اضبط المتغيّرات: `JWT_SECRET_KEY` (مفتاح قوي عشوائي — **إجباري**)، `APP_ENV=production`،
   `CORS_ORIGINS=https://your-web.vercel.app`.
4. الـ `Procfile`/`railway.json` بيشغّل `alembic upgrade head` ثم uvicorn تلقائياً.
5. بعد النشر، شغّل تعبئة المكتبة مرة: `python -m scripts.seed_food_library`.

### Web على Vercel
1. على [Vercel](https://vercel.com): New Project، و**Root Directory = `web`**.
2. متغيّر البيئة: `NEXT_PUBLIC_API_BASE_URL=https://your-backend.up.railway.app`.
3. Deploy (Next.js يُكتشف تلقائياً).

---

## 📱 بناء APK
<div dir="ltr">

```bash
cd mobile
flutter build apk --release --dart-define=API_BASE_URL=https://your-backend.up.railway.app
```
</div>

> ⚠️ المشروع على OneDrive يقفل ملفات البناء. الحل المطبّق: `mobile/build` junction لـ `C:\reshaqa_build`.
> راجع [mobile/README](mobile/README.md). الأفضل: نقل المشروع خارج OneDrive لبناء نظيف.

---

## 🔄 التحديث التلقائي (بدون إرسال يدوي)
3 مستويات (راجع [mobile/README](mobile/README.md)):
1. **الباك إند** — السعرات/المكتبة/التقارير/الرسائل على السيرفر = تحديث فوري لكل الموبايلات.
2. **Shorebird** — `shorebird patch --platforms=android --release-version=...` = تحديث Dart صامت.
3. **تحديث ذاتي** — السيرفر يستضيف آخر APK (`/app/version`)، التطبيق يعرض بانر تحديث.

---

## 🤝 ربط هواوي الصحة
الأولوية: هواوي الصحة → Health Connect → يدوي. المسار العملي: الموبايل يقرأ على الجهاز ويدفع
لـ `POST /health/sync`. خطوات تسجيل مطوّر هواوي و OAuth في [backend/README](backend/README.md).
السعرات المحروقة تُعرض كنشاط فقط ولا تُخصم من ميزانية الأكل.

---

## 🔐 الأمان
- كلمات السر **bcrypt** • كل الـ endpoints محمية بـ **JWT** • **عزل كامل** لبيانات كل مستخدم (مُدقّق).
- في الإنتاج: مفتاح JWT قوي إجباري، HTTPS، و CORS لأصول محدّدة.

*أداة توعية وليست بديلاً عن استشارة طبية.*

</div>
