"""اتجاهات الوزن — المتوسط المتحرك وكشف الثبات (plateau).

المتابعة بالاتجاه (موفينج آفريج) وليس الرقم اليومي، لأن الوزن اليومي يتذبذب
بسبب الماء والملح والهضم. كشف الثبات يعطي تنبيهاً هادئاً وداعماً فقط.
"""
from dataclasses import dataclass
from datetime import date


@dataclass
class WeightPoint:
    day: date
    weight_kg: float


@dataclass
class TrendPoint:
    day: date
    trend_kg: float          # المتوسط المتحرك
    raw_kg: float


def trailing_moving_average(
    points: list[WeightPoint], window: int = 7
) -> list[TrendPoint]:
    """متوسط متحرك خلفي بنافذة أيام (افتراضي 7) على نقاط مرتّبة زمنياً."""
    if not points:
        return []
    ordered = sorted(points, key=lambda p: p.day)
    result: list[TrendPoint] = []
    for i, p in enumerate(ordered):
        start = max(0, i - window + 1)
        window_pts = ordered[start : i + 1]
        avg = sum(w.weight_kg for w in window_pts) / len(window_pts)
        result.append(TrendPoint(day=p.day, trend_kg=round(avg, 2), raw_kg=p.weight_kg))
    return result


@dataclass
class ForecastResult:
    slope_kg_per_week: float | None
    on_track: bool                 # هل يتحرك ناحية الهدف فعلاً؟
    reached: bool                  # وصل الهدف (±0.3 كجم)
    eta_weeks: float | None        # الأسابيع المتوقعة للوصول
    eta_days: int | None


def forecast_to_goal(points: list["WeightPoint"], goal_kg: float | None) -> ForecastResult:
    """يتوقّع زمن الوصول لوزن الهدف بناءً على ميل آخر القياسات (انحدار خطي).

    on_track=False لو الاتجاه بعيد عن الهدف أو الوزن شبه ثابت أو البيانات قليلة.
    """
    slope = linear_slope_kg_per_week(points)
    if slope is None or goal_kg is None or not points:
        return ForecastResult(slope, False, False, None, None)
    current = sorted(points, key=lambda p: p.day)[-1].weight_kg
    diff = goal_kg - current  # موجب = محتاج يزيد، سالب = محتاج ينقص
    if abs(diff) <= 0.3:
        return ForecastResult(slope, True, True, 0.0, 0)
    moving_toward = (diff > 0 and slope > 0) or (diff < 0 and slope < 0)
    if not moving_toward or abs(slope) < 0.05:
        return ForecastResult(slope, False, False, None, None)
    eta_weeks = abs(diff) / abs(slope)
    return ForecastResult(slope, True, False, round(eta_weeks, 1), int(round(eta_weeks * 7)))


def linear_slope_kg_per_week(points: list[WeightPoint]) -> float | None:
    """ميل خط الانحدار للوزن مقابل الزمن (كجم/أسبوع). None لو أقل من نقطتين."""
    if len(points) < 2:
        return None
    ordered = sorted(points, key=lambda p: p.day)
    base = ordered[0].day
    xs = [(p.day - base).days for p in ordered]
    ys = [p.weight_kg for p in ordered]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return None
    slope_per_day = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    return round(slope_per_day * 7.0, 3)


@dataclass
class PlateauResult:
    is_plateau: bool
    weeks_considered: float
    net_change_kg: float
    slope_kg_per_week: float | None
    message_ar: str = ""


def detect_plateau(
    points: list[WeightPoint],
    min_days: int = 14,
    threshold_kg_per_week: float = 0.1,
    in_loss_mode: bool = True,
) -> PlateauResult:
    """يكشف ثبات الوزن خلال 2–3 أسابيع بالاتجاه.

    يعتبره ثباتاً إذا غطّت البيانات ≥ min_days وكان ميل الاتجاه قريباً من الصفر
    (لا ينزل بمعدل ملموس). تنبيه هادئ وداعم فقط عند وضع التخسيس.
    """
    if len(points) < 2:
        return PlateauResult(False, 0, 0, None)

    ordered = sorted(points, key=lambda p: p.day)
    span_days = (ordered[-1].day - ordered[0].day).days
    weeks = round(span_days / 7.0, 1)

    trend = trailing_moving_average(ordered)
    net_change = round(trend[-1].trend_kg - trend[0].trend_kg, 2)
    slope = linear_slope_kg_per_week(ordered)

    if span_days < min_days or slope is None:
        return PlateauResult(False, weeks, net_change, slope)

    # ثبات: لا نزول ملموس (الميل أعلى من -threshold، أي قريب من الصفر أو صاعد قليلاً)
    is_plateau = in_loss_mode and slope > -threshold_kg_per_week

    message = ""
    if is_plateau:
        message = (
            "وزنك ثابت تقريباً آخر "
            f"{weeks:g} أسابيع. ده طبيعي جداً في رحلة التخسيس وبيحصل للكل 💪 "
            "ممكن نراجع السعرات أو نزوّد الحركة شوية — وإنت ماشي صح، استمر!"
        )

    return PlateauResult(
        is_plateau=is_plateau,
        weeks_considered=weeks,
        net_change_kg=net_change,
        slope_kg_per_week=slope,
        message_ar=message,
    )
