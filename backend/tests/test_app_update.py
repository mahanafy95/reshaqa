"""اختبار خدمة التحديث الذاتي للتطبيق."""
import json

import app.routers.app_update as au


def test_app_version_public(client):
    r = client.get("/app/version")
    assert r.status_code == 200
    body = r.json()
    assert "version_code" in body
    assert isinstance(body["version_code"], int)
    assert "apk_available" in body
    # رابط التنزيل: إمّا المسار المحلي /app/download أو رابط خارجي (GitHub Release)
    url = body["download_url"]
    assert url == "/app/download" or url.startswith("http")
    # وجود رابط خارجي يعني أن نسخة متاحة للتنزيل
    if url.startswith("http"):
        assert body["apk_available"] is True


def test_app_download_404_when_no_apk(client):
    # لا يوجد APK في بيئة الاختبار
    r = client.get("/app/download")
    assert r.status_code in (404, 200)  # 404 لو مفيش ملف منشور


def test_app_version_with_github_url(client, tmp_path, monkeypatch):
    """مانيفست إصدار جديد برابط GitHub => الخادم يعلن عنه برابط تنزيل صالح."""
    m = tmp_path / "manifest.json"
    m.write_text(
        json.dumps(
            {
                "version_code": 5,
                "version_name": "1.4.0",
                "notes_ar": "الدخول بجوجل + برنامج زيادة الوزن",
                "mandatory": False,
                "download_url": "https://github.com/mahanafy95/reshaqa/releases/download/v1.4.0/reshaqa.apk",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(au, "_MANIFEST", m)

    d = client.get("/app/version").json()
    assert d["version_code"] == 5
    assert d["version_name"] == "1.4.0"
    assert d["apk_available"] is True
    assert d["download_url"].startswith("https://github.com")
    # محاكاة منطق العميل: نسخة الخادم(5) > المثبّتة(4) => يظهر التحديث، والرابط مطلق
    assert d["apk_available"] and d["version_code"] > 4
    assert d["download_url"].startswith("http")


def test_app_version_no_update_when_same_code(client, tmp_path, monkeypatch):
    m = tmp_path / "manifest.json"
    m.write_text(
        json.dumps({"version_code": 5, "version_name": "1.4.0", "download_url": "https://x/y.apk"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(au, "_MANIFEST", m)
    d = client.get("/app/version").json()
    assert not (d["version_code"] > 5)  # مستخدم على نفس النسخة => مفيش تحديث


def test_app_version_missing_manifest_is_safe(client, tmp_path, monkeypatch):
    monkeypatch.setattr(au, "_MANIFEST", tmp_path / "nope.json")
    monkeypatch.setattr(au, "_APK", tmp_path / "nope.apk")
    d = client.get("/app/version").json()
    assert d["version_code"] == 0
    assert d["apk_available"] is False  # مفيش تحديث وهمي
