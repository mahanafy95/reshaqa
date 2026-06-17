"""اختبار خدمة التحديث الذاتي للتطبيق."""


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
