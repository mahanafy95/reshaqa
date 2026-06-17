"""حساب التقارير الأسبوعية والشهرية — الالتزام والاتجاه.

الأسبوع من السبت إلى الجمعة. التصنيف اليومي: ضمن/فوق/تحت الهدف، أو لا يوجد تسجيل.
"""
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.profile import Profile
from ..models.targets import DailyTarget
from ..models.food import FoodLogged
from ..models.tracking import WeightLog
from . import targets_service
from .trends import WeightPoint, linear_slope_kg_per_week

TOLERANCE = 0.10

# تصنيفات الالتزام
WITHIN = "ضمن الهدف"
OVER = "فوق الهدف"
UNDER = "تحت الهدف"
NO_DATA = "لا يوجد تسجيل"


def week_start_saturday(d: date_type) -> date_type:
    """يُرجع السبت الذي يبدأ به أسبوع التاريخ المعطى (السبت→الجمعة)."""
    offset = (d.weekday() - 5) % 7  # Monday=0 ... Saturday=5
    return d - timedelta(days=offset)


@dataclass
class DayAdherence:
    day: date_type
    target_calories: float
    eaten_calories: float
    status: str


@dataclass
class WeeklyReport:
    start: date_type
    end: date_type
    days: list[DayAdherence]
    adherent_days: int          # ضمن الهدف
    logged_days: int
    avg_eaten: float
    avg_target: float
    weight_change_kg: float | None
    weight_slope_kg_week: float | None
    summary_ar: str = ""


def _target_for_day(
    db: Session, user_id: int, profile: Profile, day: date_type, live_target: float
) -> float:
    saved = db.scalar(
        select(DailyTarget).where(DailyTarget.user_id == user_id, DailyTarget.date == day)
    )
    return saved.calories if saved is not None else live_target


def _classify(target: float, eaten: float, has_log: bool) -> str:
    if not has_log:
        return NO_DATA
    if eaten > target * (1 + TOLERANCE):
        return OVER
    if eaten < target * (1 - TOLERANCE):
        return UNDER
    return WITHIN


def _eaten_by_day(db: Session, user_id: int, start: date_type, end: date_type) -> dict:
    rows = db.scalars(
        select(FoodLogged).where(
            FoodLogged.user_id == user_id, FoodLogged.date >= start, FoodLogged.date <= end
        )
    ).all()
    by_day: dict[date_type, float] = {}
    for r in rows:
        by_day[r.date] = by_day.get(r.date, 0.0) + r.calories
    return by_day


def _weight_change(db: Session, user_id: int, start: date_type, end: date_type):
    rows = db.scalars(
        select(WeightLog).where(
            WeightLog.user_id == user_id, WeightLog.date >= start, WeightLog.date <= end
        ).order_by(WeightLog.date.asc())
    ).all()
    by_day = {r.date: r.weight_kg for r in rows}
    pts = [WeightPoint(day=d, weight_kg=w) for d, w in sorted(by_day.items())]
    if len(pts) < 2:
        return None, None
    change = round(pts[-1].weight_kg - pts[0].weight_kg, 2)
    slope = linear_slope_kg_per_week(pts)
    return change, slope


def build_weekly(db: Session, user_id: int, profile: Profile, week_of: date_type) -> WeeklyReport:
    start = week_start_saturday(week_of)
    end = start + timedelta(days=6)

    result, _cw, _pl = targets_service.compute_for_user(db, user_id, profile)
    live_target = result.macros.calories

    eaten_map = _eaten_by_day(db, user_id, start, end)
    days: list[DayAdherence] = []
    for i in range(7):
        d = start + timedelta(days=i)
        target = _target_for_day(db, user_id, profile, d, live_target)
        has_log = d in eaten_map
        eaten = eaten_map.get(d, 0.0)
        days.append(DayAdherence(d, target, round(eaten), _classify(target, eaten, has_log)))

    logged = [x for x in days if x.status != NO_DATA]
    adherent = sum(1 for x in days if x.status == WITHIN)
    avg_eaten = round(sum(x.eaten_calories for x in logged) / len(logged)) if logged else 0
    avg_target = round(sum(x.target_calories for x in logged) / len(logged)) if logged else round(live_target)
    change, slope = _weight_change(db, user_id, start, end)

    if adherent >= 5:
        summary = f"أسبوع ممتاز! التزمت {adherent} أيام من 7 👏 استمر على نفس المنوال 💚"
    elif adherent >= 3:
        summary = f"أسبوع كويس، التزمت {adherent} أيام. كل أسبوع بنتحسّن 🙂"
    elif logged:
        summary = "أسبوع فيه تحديات، وده طبيعي تماماً. المهم إنك مستمر — بكرة أحسن 💚"
    else:
        summary = "مفيش تسجيل الأسبوع ده. ابدأ تسجّل أكلك عشان نتابع تقدمك سوا 🙂"

    return WeeklyReport(
        start=start, end=end, days=days, adherent_days=adherent, logged_days=len(logged),
        avg_eaten=avg_eaten, avg_target=avg_target,
        weight_change_kg=change, weight_slope_kg_week=slope, summary_ar=summary,
    )


@dataclass
class MonthlyReport:
    year: int
    month: int
    start: date_type
    end: date_type
    weeks: list[WeeklyReport] = field(default_factory=list)
    total_adherent_days: int = 0
    total_logged_days: int = 0
    avg_eaten: float = 0
    weight_change_kg: float | None = None
    summary_ar: str = ""


def _month_end(year: int, month: int) -> date_type:
    if month == 12:
        return date_type(year, 12, 31)
    return date_type(year, month + 1, 1) - timedelta(days=1)


def build_monthly(db: Session, user_id: int, profile: Profile, year: int, month: int) -> MonthlyReport:
    start = date_type(year, month, 1)
    end = _month_end(year, month)

    # الأسابيع (سبت→جمعة) التي تتقاطع مع الشهر
    weeks: list[WeeklyReport] = []
    cur = week_start_saturday(start)
    while cur <= end:
        weeks.append(build_weekly(db, user_id, profile, cur))
        cur += timedelta(days=7)

    total_adherent = sum(w.adherent_days for w in weeks)
    total_logged = sum(w.logged_days for w in weeks)
    all_logged_eaten = [d.eaten_calories for w in weeks for d in w.days if d.status != NO_DATA]
    avg_eaten = round(sum(all_logged_eaten) / len(all_logged_eaten)) if all_logged_eaten else 0
    change, _slope = _weight_change(db, user_id, start, end)

    if change is not None and change < -0.3:
        summary = f"شهر فيه تقدّم حقيقي — نزلت {abs(change):g} كجم تقريباً، والتزمت {total_adherent} يوم 👏💚"
    elif total_adherent >= 12:
        summary = f"التزام رائع: {total_adherent} يوم ضمن الهدف الشهر ده. شغل جميل!"
    elif total_logged:
        summary = "شهر فيه صعود ونزول، وده طبيعي في أي رحلة. الاستمرار هو السر 💪"
    else:
        summary = "ابدأ التسجيل المنتظم الشهر الجاي عشان نقدر نطلعلك تقرير مفيد 🙂"

    return MonthlyReport(
        year=year, month=month, start=start, end=end, weeks=weeks,
        total_adherent_days=total_adherent, total_logged_days=total_logged,
        avg_eaten=avg_eaten, weight_change_kg=change, summary_ar=summary,
    )
