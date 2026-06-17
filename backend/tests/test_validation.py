"""اختبارات التحقّق المضافة (تشديد): رفض NaN/Infinity والتواريخ المستقبلية بـ 422 بدل 500."""
import json
from datetime import date, timedelta

from tests.conftest import auth_headers

TODAY = str(date.today())


def _food_payload(**over):
    base = {
        "date": TODAY, "meal": "lunch", "name_ar": "اختبار",
        "amount": 100, "calories": 50, "protein": 1, "carbs": 5, "fat": 1,
    }
    base.update(over)
    return base


def _post_raw(client, url, obj, headers):
    """يرسل JSON خاماً يسمح برموز NaN/Infinity (التي يرفض عميل httpx ترميزها)،
    لمحاكاة طلب حقيقي يصل للخادم بهذه القيم."""
    body = json.dumps(obj, allow_nan=True, ensure_ascii=False).encode("utf-8")
    h = {**headers, "Content-Type": "application/json"}
    return client.post(url, content=body, headers=h)


def test_valid_food_log_still_accepted(client):
    """ضبط مرجعي: تسجيل سليم لازم يفضل ينجح 201."""
    h = auth_headers(client, "vu0")
    r = client.post("/foods", json=_food_payload(), headers=h)
    assert r.status_code == 201, r.text


def test_food_log_rejects_nan_calories(client):
    """NaN في السعرات: 422 وليس 500 (يمنع إفساد المجاميع)."""
    h = auth_headers(client, "vu1")
    r = _post_raw(client, "/foods", _food_payload(calories=float("nan")), h)
    assert r.status_code == 422, r.text


def test_food_log_rejects_infinity_calories(client):
    h = auth_headers(client, "vu2")
    r = _post_raw(client, "/foods", _food_payload(calories=float("inf")), h)
    assert r.status_code == 422, r.text


def test_food_log_rejects_future_date(client):
    """تاريخ بعيد في المستقبل يُرفض (السماح يوم واحد لفروق التوقيت فقط)."""
    h = auth_headers(client, "vu3")
    future = str(date.today() + timedelta(days=10))
    r = client.post("/foods", json=_food_payload(date=future), headers=h)
    assert r.status_code == 422, r.text


def test_food_log_allows_one_day_timezone_grace(client):
    """تاريخ الغد مقبول لمراعاة المستخدمين المتقدّمين عن UTC."""
    h = auth_headers(client, "vu4")
    tomorrow = str(date.today() + timedelta(days=1))
    r = client.post("/foods", json=_food_payload(date=tomorrow), headers=h)
    assert r.status_code == 201, r.text


def test_weight_rejects_nan(client):
    h = auth_headers(client, "vu5")
    r = _post_raw(client, "/weight", {"weight_kg": float("nan")}, h)
    assert r.status_code == 422, r.text


def test_weight_rejects_future_date(client):
    h = auth_headers(client, "vu6")
    future = str(date.today() + timedelta(days=30))
    r = client.post("/weight", json={"date": future, "weight_kg": 80}, headers=h)
    assert r.status_code == 422, r.text
