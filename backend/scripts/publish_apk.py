"""نشر إصدار جديد للتحديث الذاتي (يحدّث app_manifest.json).

مصدر التنزيل يدعم وضعين:
  1) رابط GitHub Release (مُستحسن — لا يثقّل Render، ولا يضخّم المستودع):
       python -m scripts.publish_apk <version_code> <version_name> "<notes_ar>" \
           https://github.com/<user>/<repo>/releases/download/v<x>/reshaqa.apk [mandatory]
  2) ملف APK محلي يُخدَّم من /app/download (للتجارب فقط):
       python -m scripts.publish_apk <version_code> <version_name> "<notes_ar>" ./reshaqa.apk [mandatory]

بعد التحديث: اعمل Deploy للباك-إند على Render عشان /app/version يرجّع الإصدار الجديد.
⚠️ مهم: ارفع الـ APK على GitHub Release الأول، وبعدها حدّث المانيفست وادفع — عشان
رابط التنزيل ما يبقاش 404 لما البانر يظهر للمستخدمين.
"""
import json
import shutil
import sys
from pathlib import Path

STATIC = Path(__file__).parent.parent / "app" / "static"


def main() -> int:
    if len(sys.argv) < 5:
        print(__doc__)
        return 1
    version_code = int(sys.argv[1])
    version_name = sys.argv[2]
    notes = sys.argv[3]
    source = sys.argv[4]  # رابط http(s) أو مسار ملف APK
    mandatory = len(sys.argv) > 5 and sys.argv[5].lower() in ("1", "true", "yes")

    manifest: dict = {
        "version_code": version_code,
        "version_name": version_name,
        "notes_ar": notes,
        "mandatory": mandatory,
    }

    STATIC.mkdir(parents=True, exist_ok=True)
    if source.lower().startswith("http"):
        # وضع الرابط الخارجي (GitHub Release) — لا ننسخ ملفاً محلياً
        manifest["download_url"] = source
        # نشيل أي APK محلي قديم لتفادي خدمته بالغلط
        local = STATIC / "reshaqa-latest.apk"
        if local.exists():
            local.unlink()
        target_desc = source
    else:
        apk_src = Path(source)
        if not apk_src.exists():
            print(f"APK not found: {apk_src}")
            return 1
        shutil.copy(apk_src, STATIC / "reshaqa-latest.apk")
        target_desc = str(STATIC / "reshaqa-latest.apk")

    (STATIC / "app_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"published v{version_code} ({version_name}) -> {target_desc}")
    print("تذكير: اعمل Deploy على Render عشان التغيير يبان للمستخدمين.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
