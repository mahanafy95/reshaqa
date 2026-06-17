"""نشر APK جديد للتحديث الذاتي.

الاستخدام:
  python -m scripts.publish_apk <path-to-apk> <version_code> <version_name> "<notes_ar>"

ينسخ الـ APK إلى app/static/reshaqa-latest.apk ويحدّث app_manifest.json.
بعد كده كل الموبايلات هتكتشف الإصدار الجديد تلقائياً.
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
    apk_src = Path(sys.argv[1])
    version_code = int(sys.argv[2])
    version_name = sys.argv[3]
    notes = sys.argv[4]
    mandatory = len(sys.argv) > 5 and sys.argv[5].lower() in ("1", "true", "yes")

    if not apk_src.exists():
        print(f"APK not found: {apk_src}")
        return 1

    STATIC.mkdir(parents=True, exist_ok=True)
    shutil.copy(apk_src, STATIC / "reshaqa-latest.apk")
    (STATIC / "app_manifest.json").write_text(
        json.dumps(
            {
                "version_code": version_code,
                "version_name": version_name,
                "notes_ar": notes,
                "mandatory": mandatory,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"published v{version_code} ({version_name}) -> {STATIC / 'reshaqa-latest.apk'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
