<div dir="rtl">

# Mobile — رشاقة (Flutter)

تطبيق الموبايل لـ"رشاقة" — واجهة عربية RTL بالكامل، يتصل بالـ backend (FastAPI).

## المميزات
- دخول/تسجيل بـ **username** + قفل بيومتري/PIN اختياري.
- الرئيسية: ملخص اليوم (سعرات + ماكروز برسائل داعمة) + تنبيه plateau + إجراءات سريعة.
- تسجيل الأكل بـ 6 طرق: **يدوي، تقدير تلقائي، مكتبة، باركود، كاميرا (OCR)، مفضلة، وصفات**.
- الوزن بالاتجاه (رسم بياني)، المياه (عدّاد + هدف)، النشاط (منفصل)، الحالة المزاجية.
- التقارير الأسبوعية/الشهرية + مشاركة PDF.
- **إشعارات**: منبّه المياه بصوت حتى في الوضع الصامت (full-screen intent + exact alarm) + تذكير الأكل + وزن الجمعة.
- **Home screen widget**: المتبقي من السعرات + إضافة سريعة.

## التشغيل
<div dir="ltr">

```bash
cd mobile
flutter pub get
# تشغيل على محاكي (يتصل بـ localhost عبر 10.0.2.2):
flutter run
# أو على جهاز حقيقي مع backend منشور:
flutter run --dart-define=API_BASE_URL=https://your-backend.up.railway.app
```
</div>

## بناء APK
<div dir="ltr">

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://your-backend.up.railway.app
# الناتج: build/app/outputs/flutter-apk/app-release.apk
```
</div>

> **التوقيع:** البناء الحالي يستخدم مفاتيح الـ debug مؤقتاً (يعمل ويثبّت). قبل النشر على Google Play
> أنشئ keystore حقيقي وحدّث `android/app/build.gradle.kts` بـ signingConfig للإصدار.

## ملاحظات Android
- `minSdk 23`، `compileSdk 35`، مع **desugaring** مفعّل (مطلوب لـ flutter_local_notifications).
- صلاحيات: الإنترنت، الكاميرا، الإشعارات، SCHEDULE_EXACT_ALARM، USE_FULL_SCREEN_INTENT، USE_BIOMETRIC.
- `usesCleartextTraffic` مفعّل للسماح بالاتصال بخادم محلي عبر http أثناء التطوير (استخدم https في الإنتاج).

## التحديث التلقائي (مهم)

كل تعديل يوصل للموبايلات **بدون إرسال يدوي**، على 3 مستويات:

1. **الباك إند** (تلقائي فوراً): منطق السعرات، مكتبة الأكلات، التقارير، الرسائل — على السيرفر، فأي تعديل فيها بيظهر فوراً على كل الموبايلات.
2. **Shorebird (تحديث صامت لتعديلات Dart):** بعد أي تعديل في الشاشات/المنطق:
<div dir="ltr">

```bash
cd mobile
C:\Users\mahmo\.shorebird\bin\shorebird.bat patch --platforms=android --release-version=1.2.0+3
```
</div>
   يوصل صامت لكل موبايل عند فتح التطبيق (auto_update مفعّل). app_id في `shorebird.yaml`.
3. **تحديث ذاتي للنسخ الكبيرة (native/إضافات):** ابنِ release جديد ثم انشره:
<div dir="ltr">

```bash
cd mobile
C:\Users\mahmo\.shorebird\bin\shorebird.bat release android --artifact=apk --flutter-version=3.44.2
cd ..\backend
.venv\Scripts\python -m scripts.publish_apk C:\reshaqa_build\app\outputs\flutter-apk\app-release.apk <code> <name> "<notes>"
```
</div>
   التطبيق يعرض بانر "تحديث جديد" تلقائياً (عبر `/app/version`).

> ⚠️ **بناء الـ APK على OneDrive:** المشروع داخل OneDrive اللي بيقفل ملفات البناء.
> الحل المطبّق: `mobile/build` عبارة عن **junction** لـ `C:\reshaqa_build` (برّه OneDrive).
> لو البناء فشل بـ AccessDenied أو الـ junction اختفى، أعد إنشاءه:
> `cmd /c rmdir /s /q "\\?\...\mobile\build"` ثم `cmd /c mklink /J "...\mobile\build" "C:\reshaqa_build"`.

## البنية
<div dir="ltr">

```
lib/
├── main.dart, app.dart        # نقطة الدخول + RTL + التوجيه + قفل
├── core/                      # الثيم + عميل HTTP (dio + JWT)
├── services/                  # api, notifications, biometric, widget
├── state/app_state.dart       # Provider (مصادقة + ملخص اليوم)
├── widgets/                   # ودجتس مشتركة
└── screens/                   # كل الشاشات
```
</div>

</div>
