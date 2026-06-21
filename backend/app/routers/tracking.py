"""راوتر المتابعة — الوزن (بالاتجاه)، الوسط، المياه، النشاط، الحالة المزاجية."""
from datetime import date as date_type
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..database import get_db
from ..models.profile import Profile
from ..models.tracking import ActivityLog, MoodLog, WaistLog, WaterLog, WeightLog
from ..models.user import User
from ..schemas.tracking import (
    ActivityIn,
    ActivityOut,
    MoodIn,
    MoodOut,
    WaistIn,
    WaistOut,
    WaterDayOut,
    WaterIn,
    WeightIn,
    WeightOut,
    WeightTrendOut,
)
from ..services.trends import (
    WeightPoint,
    detect_plateau,
    forecast_to_goal,
    trailing_moving_average,
)

router = APIRouter(tags=["المتابعة"])


class WeightForecastOut(BaseModel):
    has_goal: bool
    goal_weight_kg: float | None = None
    current_weight_kg: float | None = None
    slope_kg_per_week: float | None = None
    on_track: bool = False
    reached: bool = False
    eta_weeks: float | None = None
    eta_date: date_type | None = None
    message_ar: str


def _today(d: date_type | None) -> date_type:
    return d or date_type.today()


# ==================== الوزن ====================
@router.post("/weight", response_model=WeightOut, status_code=status.HTTP_201_CREATED)
def add_weight(
    payload: WeightIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    day = _today(payload.date)
    # تحديث وزن نفس اليوم إن وُجد، وإلا إضافة
    existing = db.scalar(
        select(WeightLog).where(WeightLog.user_id == current_user.id, WeightLog.date == day)
    )
    if existing is not None:
        existing.weight_kg = payload.weight_kg
        db.commit()
        db.refresh(existing)
        return existing
    item = WeightLog(user_id=current_user.id, date=day, weight_kg=payload.weight_kg)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/weight", response_model=list[WeightOut])
def list_weight(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.scalars(
        select(WeightLog).where(WeightLog.user_id == current_user.id).order_by(WeightLog.date.desc())
    ).all()


@router.get("/weight/trend", response_model=WeightTrendOut)
def weight_trend(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = db.scalars(
        select(WeightLog).where(WeightLog.user_id == current_user.id).order_by(WeightLog.date.asc())
    ).all()
    # نقطة واحدة لكل يوم
    by_day: dict[date_type, float] = {r.date: r.weight_kg for r in rows}
    points = [WeightPoint(day=d, weight_kg=w) for d, w in sorted(by_day.items())]

    trend = trailing_moving_average(points)
    # تنبيه الثبات مناسب لوضع التخسيس بس — في وضع الزيادة الوزن الصاعد تقدّم مش ثبات.
    in_loss_mode = True
    profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    if profile is not None and points:
        from ..models.enums import TargetMode
        from ..services.calories import determine_mode
        mode = determine_mode(points[-1].weight_kg, profile.height_cm, profile.goal_weight_kg)
        in_loss_mode = mode == TargetMode.loss
    plateau = detect_plateau(points, in_loss_mode=in_loss_mode) if len(points) >= 2 else None

    return WeightTrendOut(
        points=[{"day": t.day, "raw_kg": t.raw_kg, "trend_kg": t.trend_kg} for t in trend],
        current_trend_kg=trend[-1].trend_kg if trend else None,
        slope_kg_per_week=plateau.slope_kg_per_week if plateau else None,
        plateau=plateau.__dict__ if plateau else None,
    )


@router.get("/weight/forecast", response_model=WeightForecastOut)
def weight_forecast(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> WeightForecastOut:
    """توقّع زمن الوصول لوزن الهدف بناءً على اتجاه قياساتك (تحفيز أسبوعي)."""
    profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    goal = profile.goal_weight_kg if profile else None

    rows = db.scalars(
        select(WeightLog).where(WeightLog.user_id == current_user.id).order_by(WeightLog.date.asc())
    ).all()
    by_day: dict[date_type, float] = {r.date: r.weight_kg for r in rows}
    points = [WeightPoint(day=d, weight_kg=w) for d, w in sorted(by_day.items())]
    current = points[-1].weight_kg if points else None

    if goal is None:
        return WeightForecastOut(
            has_goal=False, current_weight_kg=current,
            message_ar="حدّد وزن هدفك من ملفك الشخصي عشان نقدر نتوقّعلك وصولك ليه 🎯",
        )

    fc = forecast_to_goal(points, goal)
    eta_date = (date_type.today() + timedelta(days=fc.eta_days)) if fc.eta_days else None

    if fc.slope_kg_per_week is None:
        msg = "سجّل وزنك كذا مرة على مدى أيام وهنوريك متوقّع توصل هدفك إمتى 📈"
    elif fc.reached:
        msg = "مبروووك! وصلت وزن هدفك تقريباً 🎉 حافظ عليه."
    elif fc.on_track and fc.eta_weeks:
        wk = fc.eta_weeks
        wk_txt = f"{wk:g} أسبوع" if wk >= 1 else "أقل من أسبوع"
        date_txt = f" (حوالي {eta_date})" if eta_date else ""
        msg = f"بمعدّلك الحالي ({fc.slope_kg_per_week:g} كجم/أسبوع) متوقّع توصل هدفك خلال ~{wk_txt}{date_txt} 💪"
    elif abs(fc.slope_kg_per_week) < 0.05:
        msg = "وزنك ثابت تقريباً — لو عايز تتحرّك ناحية هدفك عدّل سعراتك أو نشاطك شوية."
    else:
        msg = "اتجاهك الحالي بعيد عن هدفك — راجع نظامك وهنوصل سوا 🙏"

    return WeightForecastOut(
        has_goal=True, goal_weight_kg=goal, current_weight_kg=current,
        slope_kg_per_week=fc.slope_kg_per_week, on_track=fc.on_track, reached=fc.reached,
        eta_weeks=fc.eta_weeks, eta_date=eta_date, message_ar=msg,
    )


# ==================== الوسط (اختياري ومنفصل) ====================
@router.post("/waist", response_model=WaistOut, status_code=status.HTTP_201_CREATED)
def add_waist(
    payload: WaistIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    item = WaistLog(user_id=current_user.id, date=_today(payload.date), waist_cm=payload.waist_cm)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/waist", response_model=list[WaistOut])
def list_waist(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(WaistLog).where(WaistLog.user_id == current_user.id).order_by(WaistLog.date.desc())
    ).all()


# ==================== المياه ====================
def _water_goal_ml(db: Session, user_id: int) -> int:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is not None:
        return int(min(max(profile.weight_kg * 35, 1500), 4000))
    return 2500


@router.post("/water", response_model=WaterDayOut, status_code=status.HTTP_201_CREATED)
def add_water(
    payload: WaterIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    day = _today(payload.date)
    db.add(WaterLog(user_id=current_user.id, date=day, ml=payload.ml))
    db.commit()
    return _water_day(db, current_user.id, day)


@router.get("/water", response_model=WaterDayOut)
def get_water(
    on: date_type | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _water_day(db, current_user.id, _today(on))


def _water_day(db: Session, user_id: int, day: date_type) -> WaterDayOut:
    rows = db.scalars(
        select(WaterLog).where(WaterLog.user_id == user_id, WaterLog.date == day)
    ).all()
    total = sum(r.ml for r in rows)
    goal = _water_goal_ml(db, user_id)
    remaining = max(goal - total, 0)
    percent = int(round(total / goal * 100)) if goal else 0
    if total >= goal:
        msg = "وصلت لهدف المياه النهاردة 💧 تمام!"
    elif percent >= 50:
        msg = "نص الطريق خلص، كمّل شرب مياه 👍"
    else:
        msg = "متنساش تشرب مياه على مدار اليوم 💧"
    return WaterDayOut(
        date=day, total_ml=total, goal_ml=goal, remaining_ml=remaining, percent=percent, message_ar=msg
    )


# ==================== النشاط (منفصل، لا يُخصم من ميزانية الأكل) ====================
@router.post("/activity", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def add_activity(
    payload: ActivityIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    item = ActivityLog(
        user_id=current_user.id,
        date=_today(payload.date),
        type_ar=payload.type_ar,
        duration_min=payload.duration_min,
        calories_burned=payload.calories_burned,
        steps=payload.steps,
        source=payload.source,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/activity", response_model=list[ActivityOut])
def list_activity(
    on: date_type | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    day = _today(on)
    return db.scalars(
        select(ActivityLog)
        .where(ActivityLog.user_id == current_user.id, ActivityLog.date == day)
        .order_by(ActivityLog.created_at)
    ).all()


@router.delete("/activity/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    item = db.scalar(
        select(ActivityLog).where(
            ActivityLog.id == activity_id, ActivityLog.user_id == current_user.id
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="النشاط غير موجود.")
    db.delete(item)
    db.commit()


# ==================== الحالة المزاجية ====================
@router.put("/mood", response_model=MoodOut)
def upsert_mood(
    payload: MoodIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    day = _today(payload.date)
    item = db.scalar(
        select(MoodLog).where(MoodLog.user_id == current_user.id, MoodLog.date == day)
    )
    if item is None:
        item = MoodLog(user_id=current_user.id, date=day)
        db.add(item)
    item.energy = payload.energy
    item.sleep_hours = payload.sleep_hours
    item.hunger = payload.hunger
    db.commit()
    db.refresh(item)
    return item


@router.get("/mood", response_model=MoodOut | None)
def get_mood(
    on: date_type | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    day = _today(on)
    return db.scalar(
        select(MoodLog).where(MoodLog.user_id == current_user.id, MoodLog.date == day)
    )
