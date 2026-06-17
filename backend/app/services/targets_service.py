"""تنسيق حساب أهداف المستخدم — يجمع المحرك مع أحدث وزن وكشف الثبات.

الأهداف تُحسب دائماً من أحدث وزن مسجّل (أو وزن الملف الشخصي)، فتتعدّل تلقائياً
مع تغيّر الوزن، وتتحوّل لوضع التثبيت عند الوصول للهدف.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.enums import TargetMode
from ..models.profile import Profile
from ..models.tracking import WeightLog
from . import calories as C
from .trends import PlateauResult, WeightPoint, detect_plateau


def get_current_weight(db: Session, user_id: int, profile: Profile) -> float:
    """أحدث وزن مسجّل للمستخدم، أو وزن الملف الشخصي إن لم يوجد تسجيل."""
    latest = db.scalar(
        select(WeightLog)
        .where(WeightLog.user_id == user_id)
        .order_by(WeightLog.date.desc(), WeightLog.created_at.desc())
        .limit(1)
    )
    return latest.weight_kg if latest is not None else profile.weight_kg


def _weight_points(db: Session, user_id: int) -> list[WeightPoint]:
    rows = db.scalars(
        select(WeightLog).where(WeightLog.user_id == user_id).order_by(WeightLog.date.asc())
    ).all()
    # نقطة واحدة لكل يوم (آخر تسجيل في اليوم) لتفادي ازدواج نقاط نفس اليوم
    by_day: dict = {}
    for r in rows:
        by_day[r.date] = r.weight_kg
    return [WeightPoint(day=d, weight_kg=w) for d, w in sorted(by_day.items())]


def compute_for_user(
    db: Session, user_id: int, profile: Profile
) -> tuple[C.TargetResult, float, PlateauResult | None]:
    """يحسب الأهداف الحالية + الوزن الحالي + إشارة الثبات."""
    current_weight = get_current_weight(db, user_id, profile)

    result = C.compute_targets(
        sex=profile.sex,
        age=profile.age,
        height_cm=profile.height_cm,
        weight_kg=current_weight,
        activity_level=profile.activity_level,
        goal_weight_kg=profile.goal_weight_kg,
        goal_rate_kg_week=profile.goal_rate,
    )

    points = _weight_points(db, user_id)
    plateau = None
    if len(points) >= 2:
        plateau = detect_plateau(points, in_loss_mode=result.mode == TargetMode.loss)

    return result, current_weight, plateau
