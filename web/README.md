<div dir="rtl">

# Web Dashboard — رشاقة (Next.js)

لوحة تحكم على الويب بنفس صلاحيات الموبايل: دخول، تسجيل، عرض، وتقارير — عربي RTL بالكامل.

**التقنية:** Next.js 14 (App Router) · Tailwind CSS · recharts · TypeScript

## التشغيل المحلي
<div dir="ltr">

```bash
cd web
npm install
# عدّل web/.env.local: NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev      # http://localhost:3000
```
</div>

> لازم الـ backend يكون شغّال (محلياً على 8000، أو رابط Railway في الإنتاج).

## البناء
<div dir="ltr">

```bash
npm run build && npm start
```
</div>

## النشر على Vercel
1. ارفع المشروع على GitHub.
2. على [Vercel](https://vercel.com): New Project → اختر الريبو → **Root Directory = `web`**.
3. أضف متغير البيئة: `NEXT_PUBLIC_API_BASE_URL` = رابط الـ backend على Railway.
4. Deploy. (الإطار Next.js يتعرّف عليه تلقائياً.)

## الصفحات
| المسار | الوصف |
|--------|-------|
| `/login` | دخول/تسجيل بـ username |
| `/dashboard` | ملخص اليوم + ماكروز + plateau + المياه |
| `/dashboard/foods` | تسجيل أكل: بحث المكتبة + تقدير تلقائي + يدوي + قائمة اليوم |
| `/dashboard/weight` | الوزن + رسم الاتجاه (موفينج آفريج) |
| `/dashboard/water` | المياه (عدّاد + هدف + مشروبات) |
| `/dashboard/activity` | النشاط (منفصل) |
| `/dashboard/mood` | الحالة المزاجية |
| `/dashboard/reports` | تقارير مفصّلة + رسم الالتزام + تنزيل PDF |
| `/dashboard/profile` | بياناتي (مع منع الوزن غير الصحي) |

## ملاحظات
- المصادقة: JWT في `localStorage`، يُحقن تلقائياً في كل طلب.
- `.next/` و `node_modules/` خارج git.
- على OneDrive: لو `next build` فشل بقفل ملفات، شغّله بعد إيقاف مزامنة OneDrive مؤقتاً.

</div>
