"""اختبارات تصدير بيانات المستخدم (GET /export → CSV)."""
from datetime import date

from tests.conftest import auth_headers


def test_export_requires_auth(client):
    assert client.get("/export").status_code == 401


def test_export_returns_csv_with_logged_food(client):
    h = auth_headers(client, "exp_user")
    today = date.today().isoformat()
    r = client.post(
        "/foods",
        json={"date": today, "meal": "lunch", "name_ar": "كشري", "amount": 300, "calories": 480,
              "protein": 12, "carbs": 80, "fat": 9},
        headers=h,
    )
    assert r.status_code in (200, 201), r.text

    e = client.get("/export", headers=h)
    assert e.status_code == 200, e.text
    assert "text/csv" in e.headers.get("content-type", "")
    assert "attachment" in e.headers.get("content-disposition", "")
    body = e.content.decode("utf-8")
    assert "كشري" in body
    assert "الأكل المسجّل" in body
    assert "الوزن" in body  # الأقسام موجودة حتى لو فاضية


def test_export_empty_user_still_ok(client):
    h = auth_headers(client, "exp_empty")
    e = client.get("/export", headers=h)
    assert e.status_code == 200, e.text
    assert "رشاقة" in e.content.decode("utf-8")
