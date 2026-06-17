"""حساب التقارير الأسبوعية والشهرية — الالتزام والاتجاه (تقارير مفصّلة).

الأسبوع من السبت إلى الجمعة. التصنيف اليومي: ضمن/فوق/تحت الهدف، أو لا يوجد تسجيل.
التقارير تشمل: السعرات والماكروز، توزيع الأيام، المياه، النشاط، واتجاه الوزن.
"""
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.food import FoodLogged
from ..models.profile import Profile
from ..models.targets import DailyTarget
from ..models.tracking import ActivityLog, WaterLog, WeightLog
from . import targets_service
from .trends import WeightPoint, linear_slope_kg_per_week

TOLERANCE = 0.10

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
    protein: float
    carbs: float
    fat: float
    status: str


@dataclass
class WeeklyReport:
    start: date_type
    end: date_type
    days: list[DayAdherence]
    adherent_days: int
    logged_days: int
    days_within: int
    days_over: int
    days_under: int
    avg_eaten: float
    avg_target: float
    avg_protein: float
    avg_carbs: float
    avg_fat: float
    best_day: date_type | None
    water_avg_ml: int
    activity_total_min: int
    activity_total_calories: int
    activity_sessions: int
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


def _logged_by_day(db: Session, user_id: int, start: date_type, end: date_type) -> dict:
    """قاموس {اليوم: {cal,p,c,f}} من سجلات الأكل."""
    rows = db.scalars(
        select(FoodLogged).where(
            FoodLogged.user_id == user_id, FoodLogged.date >= start, FoodLogged.date <= end
        )
    ).all()
    by_day: dict[date_type, dict] = {}
    for r in rows:
        d = by_day.setdefault(r.date, {"cal": 0.0, "p": 0.0, "c": 0.0, "f": 0.0})
        d["cal"] += r.calories
        d["p"] += r.protein
        d["c"] += r.carbs
        d["f"] += r.fat
    return by_day


def _period_water(db: Session, user_id: int, start: date_type, end: date_type) -> tuple[int, int]:
    rows = db.scalars(
        select(WaterLog).where(
            WaterLog.user_id == user_id, WaterLog.date >= start, WaterLog.date <= end
        )
    ).all()
    by_day: dict[date_type, int] = {}
    for r in rows:
        by_day[r.date] = by_day.get(r.date, 0) + r.ml
    if not by_day:
        return 0, 0
    avg = round(sum(by_day.values()) / len(by_day))
    return avg, len(by_day)


def _period_activity(db: Session, user_id: int, start: date_type, end: date_type) -> tuple[int, int, int]:
    rows = db.scalars(
        select(ActivityLog).where(
            ActivityLog.user_id == user_id, ActivityLog.date >= start, ActivityLog.date <= end
        )
    ).all()
    total_min = sum(r.duration_min or 0 for r in rows)
    total_cal = round(sum(r.calories_burned or 0 for r in rows))
    return total_min, total_cal, len(rows)


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

    logged = _logged_by_day(db, user_id, start, end)
    days: list[DayAdherence] = []
    for i in range(7):
        d = start + timedelta(days=i)
        target = _target_for_day(db, user_id, profile, d, live_target)
        data = logged.get(d)
        has_log = data is not None
        days.append(DayAdherence(
            day=d, target_calories=target,
            eaten_calories=round(data["cal"]) if data else 0,
            protein=round(data["p"], 1) if data else 0,
            carbs=round(data["c"], 1) if data else 0,
            fat=round(data["f"], 1) if data else 0,
            status=_classify(target, data["cal"] if data else 0, has_log),
        ))

    logged_days = [x for x in days if x.status != NO_DATA]
    within = sum(1 for x in days if x.status == WITHIN)
    over = sum(1 for x in days if x.status == OVER)
    under = sum(1 for x in days if x.status == UNDER)

    n = len(logged_days) or 1
    avg_eaten = round(sum(x.eaten_calories for x in logged_days) / n) if logged_days else 0
    avg_target = round(sum(x.target_calories for x in logged_days) / n) if logged_days else round(live_target)
    avg_p = round(sum(x.protein for x in logged_days) / n, 1) if logged_days else 0
    avg_c = round(sum(x.carbs for x in logged_days) / n, 1) if logged_days else 0
    avg_f = round(sum(x.fat for x in logged_days) / n, 1) if logged_days else 0

    # أفضل يوم: الأقرب للهدف بين الأيام المسجّلة
    best = None
    if logged_days:
        best = min(logged_days, key=lambda x: abs(x.eaten_calories - x.target_calories)).day

    water_avg, _water_days = _period_water(db, user_id, start, end)
    act_min, act_cal, act_sessions = _period_activity(db, user_id, start, end)
    change, slope = _weight_change(db, user_id, start, end)

    if within >= 5:
        summary = f"أسبوع ممتاز! التزمت {within} أيام من 7 👏 استمر على نفس المنوال 💚"
    elif within >= 3:
        summary = f"أسبوع كويس، التزمت {within} أيام. كل أسبوع بنتحسّن 🙂"
    elif logged_days:
        summary = "أسبوع فيه تحديات، وده طبيعي تماماً. المهم إنك مستمر — بكرة أحسن 💚"
    else:
        summary = "مفيش تسجيل الأسبوع ده. ابدأ تسجّل أكلك عشان نتابع تقدمك سوا 🙂"

    return WeeklyReport(
        start=start, end=end, days=days, adherent_days=within, logged_days=len(logged_days),
        days_within=within, days_over=over, days_under=under,
        avg_eaten=avg_eaten, avg_target=avg_target,
        avg_protein=avg_p, avg_carbs=avg_c, avg_fat=avg_f, best_day=best,
        water_avg_ml=water_avg, activity_total_min=act_min,
        activity_total_calories=act_cal, activity_sessions=act_sessions,
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
    avg_protein: float = 0
    avg_carbs: float = 0
    avg_fat: float = 0
    water_avg_ml: int = 0
    activity_total_min: int = 0
    activity_total_calories: int = 0
    weight_change_kg: float | None = None
    summary_ar: str = ""


def _month_end(year: int, month: int) -> date_type:
    if month == 12:
        return date_type(year, 12, 31)
    return date_type(year, month + 1, 1) - timedelta(days=1)


def build_monthly(db: Session, user_id: int, profile: Profile, year: int, month: int) -> MonthlyReport:
    start = date_type(year, month, 1)
    end = _month_end(year, month)

    weeks: list[WeeklyReport] = []
    cur = week_start_saturday(start)
    while cur <= end:
        weeks.append(build_weekly(db, user_id, profile, cur))
        cur += timedelta(days=7)

    total_adherent = sum(w.adherent_days for w in weeks)
    total_logged = sum(w.logged_days for w in weeks)
    logged_days = [d for w in weeks for d in w.days if d.status != NO_DATA]
    nn = len(logged_days) or 1
    avg_eaten = round(sum(d.eaten_calories for d in logged_days) / nn) if logged_days else 0
    avg_p = round(sum(d.protein for d in logged_days) / nn, 1) if logged_days else 0
    avg_c = round(sum(d.carbs for d in logged_days) / nn, 1) if logged_days else 0
    avg_f = round(sum(d.fat for d in logged_days) / nn, 1) if logged_days else 0

    water_avg, _wd = _period_water(db, user_id, start, end)
    act_min, act_cal, _sessions = _period_activity(db, user_id, start, end)
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
        avg_eaten=avg_eaten, avg_protein=avg_p, avg_carbs=avg_c, avg_fat=avg_f,
        water_avg_ml=water_avg, activity_total_min=act_min, activity_total_calories=act_cal,
        weight_change_kg=change, summary_ar=summary,
    )
