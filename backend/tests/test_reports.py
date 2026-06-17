"""اختبارات التقارير الأسبوعية والشهرية + تصدير PDF."""
from datetime import date, timedelta

from app.services.reports import week_start_saturday
from tests.conftest import auth_headers

PROFILE = {
    "age": 30, "sex": "male", "height_cm": 180, "weight_kg": 90,
    "activity_level": "moderate", "goal_weight_kg": 78, "goal_rate": 0.5,
}
WEEK_OF = date(2026, 3, 4)


def test_week_start_saturday():
    # 2026-03-07 سبت => يبدأ بنفسه ; 2026-03-06 جمعة => يبدأ بالسبت السابق
    sat = date(2026, 3, 7)
    assert week_start_saturday(sat) == sat
    fri = date(2026, 3, 6)
    assert week_start_saturday(fri) == date(2026, 2, 28)


def _setup(client, username):
    h = auth_headers(client, username)
    client.put("/profile", json=PROFILE, headers=h)
    target = client.get("/targets", headers=h).json()["target_calories"]
    return h, target


def _log(client, h, day, cals):
    client.post("/foods", json={"date": day.isoformat(), "meal": "lunch", "name_ar": "أكل",
                                "amount": 100, "calories": cals}, headers=h)


def test_weekly_report_adherence(client):
    h, target = _setup(client, "rep1")
    start = week_start_saturday(WEEK_OF)
    _log(client, h, start, target)               # ضمن الهدف
    _log(client, h, start + timedelta(days=1), target * 1.6)  # فوق
    _log(client, h, start + timedelta(days=2), target * 0.4)  # تحت

    r = client.get(f"/reports/weekly?week_of={WEEK_OF.isoformat()}", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["days"]) == 7
    statuses = [d["status"] for d in body["days"]]
    assert "ضمن الهدف" in statuses
    assert "فوق الهدف" in statuses
    assert "تحت الهدف" in statuses
    assert body["adherent_days"] >= 1
    assert body["logged_days"] == 3
    assert body["summary_ar"]
    # تفاصيل إضافية
    assert body["days_within"] + body["days_over"] + body["days_under"] == 3
    assert "avg_protein" in body and "avg_carbs" in body and "avg_fat" in body
    assert "water_avg_ml" in body and "activity_total_min" in body
    # ماكروز كل يوم متاحة
    assert all("protein" in d for d in body["days"])


def test_monthly_report_shape(client):
    h, target = _setup(client, "rep2")
    _log(client, h, date(2026, 3, 10), target)
    r = client.get("/reports/monthly?year=2026&month=3", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["year"] == 2026 and body["month"] == 3
    assert len(body["weeks"]) >= 4
    assert body["summary_ar"]


def test_weekly_pdf_export(client):
    h, target = _setup(client, "rep3")
    _log(client, h, week_start_saturday(WEEK_OF), target)
    r = client.get(f"/reports/weekly.pdf?week_of={WEEK_OF.isoformat()}", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 800


def test_monthly_pdf_export(client):
    h, _ = _setup(client, "rep4")
    r = client.get("/reports/monthly.pdf?year=2026&month=3", headers=h)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_reports_require_profile(client):
    h = auth_headers(client, "rep5")
    r = client.get("/reports/weekly", headers=h)
    assert r.status_code == 400
