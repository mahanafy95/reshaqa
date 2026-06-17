"""راوتر التحديث الذاتي للتطبيق — يستضيف آخر نسخة APK ويعلن عنها.

التطبيق يفحص /app/version عند الفتح؛ لو نسخة الخادم أحدث، ينزّل /app/download
ويعرض زر التثبيت. كده أي إصدار جديد يوصل لكل الموبايلات تلقائياً بدون إرسال يدوي.
"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/app", tags=["تحديث التطبيق"])

_STATIC = Path(__file__).parent.parent / "static"
_MANIFEST = _STATIC / "app_manifest.json"
_APK = _STATIC / "reshaqa-latest.apk"


@router.get("/version")
def app_version() -> dict:
    """يُرجع آخر إصدار متاح على الخادم."""
    if _MANIFEST.exists():
        try:
            data = json.loads(_MANIFEST.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}
    # رابط التنزيل: خارجي (مثل GitHub Release) إن وُجد في المانيفست، وإلا الملف المحلي
    external_url = data.get("download_url")
    return {
        "version_code": int(data.get("version_code", 0)),
        "version_name": data.get("version_name", "0"),
        "notes_ar": data.get("notes_ar", ""),
        "mandatory": bool(data.get("mandatory", False)),
        "apk_available": bool(external_url) or _APK.exists(),
        "download_url": external_url or "/app/download",
    }


@router.get("/download")
def app_download() -> FileResponse:
    """تنزيل آخر APK منشور."""
    if not _APK.exists():
        raise HTTPException(status_code=404, detail="لا يوجد ملف APK منشور حالياً.")
    return FileResponse(
        str(_APK),
        media_type="application/vnd.android.package-archive",
        filename="reshaqa.apk",
    )
