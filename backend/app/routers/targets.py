"""راوتر الأهداف اليومية — حساب تلقائي من أحدث وزن + حفظ هدف اليوم."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..database import get_db
from ..models.profile import Profile
from ..models.targets import DailyTarget
from ..models.user import User
from ..schemas.targets import DailyTargetOut, MacrosOut, PlateauOut, TargetOut
from ..services import targets_service

router = APIRouter(prefix="/targets", tags=["الأهداف"])


def _require_profile(db: Session, user_id: int) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="أكمل ملفك الشخصي الأول عشان نحسب أهدافك.",
        )
    return profile


def _build_out(result, current_weight, plateau) -> TargetOut:
    return TargetOut(
        bmr=result.bmr,
        tdee=result.tdee,
        mode=result.mode,
        target_calories=result.target_calories,
        deficit_applied=result.deficit_applied,
        floored_to_safe_min=result.floored_to_safe_min,
        macros=MacrosOut(
            calories=result.macros.calories,
            protein_g=result.macros.protein_g,
            carbs_g=result.macros.carbs_g,
            fat_g=result.macros.fat_g,
        ),
        bmi=result.bmi,
        current_weight_kg=current_weight,
        messages_ar=result.messages_ar,
        plateau=PlateauOut(**plateau.__dict__) if plateau is not None else None,
    )


@router.get("", response_model=TargetOut)
def current_targets(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """يحسب الأهداف الحالية من أحدث وزن (يتعدّل تلقائياً مع تغيّر الوزن)."""
    profile = _require_profile(db, current_user.id)
    result, current_weight, plateau = targets_service.compute_for_user(
        db, current_user.id, profile
    )
    return _build_out(result, current_weight, plateau)


@router.post("/today", response_model=DailyTargetOut)
def save_today_target(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """يحسب ويحفظ هدف اليوم (upsert) — يُستخدم كلقطة ثابتة لليوم."""
    profile = _require_profile(db, current_user.id)
    result, _cw, _pl = targets_service.compute_for_user(db, current_user.id, profile)

    today = date.today()
    target = db.scalar(
        select(DailyTarget).where(
            DailyTarget.user_id == current_user.id, DailyTarget.date == today
        )
    )
    if target is None:
        target = DailyTarget(user_id=current_user.id, date=today)
        db.add(target)

    target.calories = result.macros.calories
    target.protein_g = result.macros.protein_g
    target.carbs_g = result.macros.carbs_g
    target.fat_g = result.macros.fat_g
    target.mode = result.mode
    target.floored_to_safe_min = result.floored_to_safe_min

    db.commit()
    db.refresh(target)
    return DailyTargetOut.model_validate(target)
