"""اختبارات توقّع الوصول لوزن الهدف (forecast_to_goal + GET /weight/forecast)."""
from datetime import date, timedelta

from app.services.trends import WeightPoint, forecast_to_goal
from tests.conftest import auth_headers


def _pts(start_kg: float, daily_delta: float, n: int):
    base = date(2026, 1, 1)
    return [WeightPoint(day=base + timedelta(days=i), weight_kg=start_kg + daily_delta * i) for i in range(n)]


def test_forecast_on_track_loss():
    pts = _pts(91.0, -0.1, 11)  # آخر وزن 90، ينزل ~0.7 كجم/أسبوع، الهدف 85
    r = forecast_to_goal(pts, 85.0)
    assert r.on_track is True and r.reached is False
    assert r.slope_kg_per_week is not None and r.slope_kg_per_week < 0
    assert r.eta_weeks is not None and 6 < r.eta_weeks < 9
    assert r.eta_days is not None and r.eta_days > 0


def test_forecast_on_track_gain():
    pts = _pts(60.0, 0.05, 11)  # بيزيد، الهدف أعلى
    r = forecast_to_goal(pts, 65.0)
    assert r.on_track is True
    assert r.slope_kg_per_week is not None and r.slope_kg_per_week > 0
    assert r.eta_weeks is not None


def test_forecast_wrong_direction_not_on_track():
    pts = _pts(85.0, 0.1, 11)  # بيزيد لكن الهدف أقل
    r = forecast_to_goal(pts, 80.0)
    assert r.on_track is False and r.eta_weeks is None


def test_forecast_reached_goal():
    pts = _pts(85.1, -0.02, 11)  # آخر وزن ~84.9 ضمن ±0.3 من 85
    r = forecast_to_goal(pts, 85.0)
    assert r.reached is True and r.on_track is True


def test_forecast_insufficient_data():
    r = forecast_to_goal([WeightPoint(day=date(2026, 1, 1), weight_kg=90.0)], 85.0)
    assert r.slope_kg_per_week is None and r.on_track is False and r.eta_weeks is None


def test_forecast_no_goal_kg():
    r = forecast_to_goal(_pts(90.0, -0.1, 5), None)
    assert r.on_track is False and r.eta_weeks is None


# ---------- نقطة النهاية ----------
def test_forecast_endpoint_no_goal(client):
    h = auth_headers(client, "fc_nogoal")
    r = client.get("/weight/forecast", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_goal"] is False
    assert body["message_ar"]
