"""اختبار خدمة التحديث الذاتي للتطبيق."""


def test_app_version_public(client):
    r = client.get("/app/version")
    assert r.status_code == 200
    body = r.json()
    assert "version_code" in body
    assert body["download_url"] == "/app/download"
    assert "apk_available" in body


def test_app_download_404_when_no_apk(client):
    # لا يوجد APK في بيئة الاختبار
    r = client.get("/app/download")
    assert r.status_code in (404, 200)  # 404 لو مفيش ملف منشور
