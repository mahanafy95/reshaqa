"""اختبارات اتجاهات الوزن وكشف الثبات."""
from datetime import date, timedelta

from app.services.trends import (
    WeightPoint,
    detect_plateau,
    linear_slope_kg_per_week,
    trailing_moving_average,
)

START = date(2026, 1, 1)


def _pts(values: list[float]) -> list[WeightPoint]:
    return [WeightPoint(day=START + timedelta(days=i), weight_kg=v) for i, v in enumerate(values)]


def test_moving_average_smooths():
    pts = _pts([80, 82, 78, 80, 81, 79, 80])
    trend = trailing_moving_average(pts, window=7)
    assert len(trend) == 7
    # آخر نقطة = متوسط الكل
    assert trend[-1].trend_kg == round(sum([80, 82, 78, 80, 81, 79, 80]) / 7, 2)


def test_slope_declining_is_negative():
    # نزول 2 كجم خلال 21 يوم
    vals = [80 - (2 * i / 20) for i in range(21)]
    slope = linear_slope_kg_per_week(_pts(vals))
    assert slope is not None and slope < 0


def test_plateau_detected_when_flat():
    # وزن ثابت ~80 لمدة 21 يوم
    vals = [80 + (0.1 if i % 2 else -0.1) for i in range(21)]
    res = detect_plateau(_pts(vals))
    assert res.is_plateau is True
    assert res.message_ar  # رسالة داعمة موجودة


def test_no_plateau_when_declining():
    vals = [80 - (3 * i / 20) for i in range(21)]  # نزول 3 كجم
    res = detect_plateau(_pts(vals))
    assert res.is_plateau is False


def test_no_plateau_insufficient_days():
    vals = [80, 80, 80, 80, 80]  # 5 أيام فقط
    res = detect_plateau(_pts(vals))
    assert res.is_plateau is False


def test_plateau_only_in_loss_mode():
    vals = [80 + (0.1 if i % 2 else -0.1) for i in range(21)]
    res = detect_plateau(_pts(vals), in_loss_mode=False)
    assert res.is_plateau is False
