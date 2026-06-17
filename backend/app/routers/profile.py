"""راوتر الملف الشخصي — إنشاء/تعديل/عرض، مع منع الوزن المستهدف غير الصحي."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..database import get_db
from ..models.profile import Profile
from ..models.tracking import WeightLog
from ..models.user import User
from ..schemas.profile import ProfileIn, ProfileOut
from ..services.body_metrics import healthy_weight_range
from ..services.calories import validate_goal_weight

router = APIRouter(prefix="/profile", tags=["الملف الشخصي"])


def _to_out(profile: Profile) -> ProfileOut:
    out = ProfileOut.model_validate(profile)
    lo, hi = healthy_weight_range(profile.height_cm)
    out.healthy_min_kg = lo
    out.healthy_max_kg = hi
    return out


def _validate_goal(payload: ProfileIn) -> None:
    if payload.goal_weight_kg is not None:
        v = validate_goal_weight(payload.goal_weight_kg, payload.height_cm)
        if not v.is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": v.message_ar,
                    "healthy_min_kg": v.healthy_min_kg,
                    "healthy_max_kg": v.healthy_max_kg,
                    "suggested_goal_kg": v.suggested_goal_kg,
                },
            )


def _upsert_today_weight(db: Session, user_id: int, weight_kg: float) -> None:
    """يسجّل/يحدّث وزن اليوم ليكون لدى محرك الاتجاه بيانات."""
    today = date.today()
    existing = db.scalar(
        select(WeightLog).where(WeightLog.user_id == user_id, WeightLog.date == today)
    )
    if existing is None:
        db.add(WeightLog(user_id=user_id, date=today, weight_kg=weight_kg))
    else:
        existing.weight_kg = weight_kg


@router.get("", response_model=ProfileOut)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="لسه ما عملتش ملفك الشخصي. أكمل بياناتك عشان نحسب أهدافك.",
        )
    return _to_out(profile)


@router.put("", response_model=ProfileOut)
def upsert_profile(
    payload: ProfileIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_goal(payload)

    profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    if profile is None:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    profile.age = payload.age
    profile.sex = payload.sex
    profile.height_cm = payload.height_cm
    profile.weight_kg = payload.weight_kg
    profile.activity_level = payload.activity_level
    profile.goal_weight_kg = payload.goal_weight_kg
    profile.goal_rate = payload.goal_rate

    _upsert_today_weight(db, current_user.id, payload.weight_kg)

    db.commit()
    db.refresh(profile)
    return _to_out(profile)
