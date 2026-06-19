"""راوتر الملخص اليومي ومؤشرات الجسم واقتراح المشروبات والتحفيز (Streaks)."""
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..database import get_db
from ..models.profile import Profile
from ..models.tracking import WaistLog
from ..models.user import User
from ..schemas.summary import BodyMetricsOut, DailySummaryOut, DrinkSuggestion
from ..services import body_metrics as BM
from ..services import gamification
from ..services import summary_service
from ..services.targets_service import get_current_weight

router = APIRouter(tags=["الملخص والمؤشرات"])


class AchievementOut(BaseModel):
    key: str
    title_ar: str
    emoji: str
    unlocked: bool


class StreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    total_days_logged: int
    achievements: list[AchievementOut] = []


def _require_profile(db: Session, user_id: int) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="أكمل ملفك الشخصي الأول.",
        )
    return profile


@router.get("/summary", response_model=DailySummaryOut)
def daily_summary(
    on: date_type | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _require_profile(db, current_user.id)
    day = on or date_type.today()
    return summary_service.build_summary(db, current_user.id, profile, day)


@router.get("/metrics/body", response_model=BodyMetricsOut)
def body_metrics(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    profile = _require_profile(db, current_user.id)
    weight = get_current_weight(db, current_user.id, profile)
    bmi_val = BM.bmi(weight, profile.height_cm)
    lo, hi = BM.healthy_weight_range(profile.height_cm)
    bf = BM.body_fat_deurenberg(bmi_val, profile.age, profile.sex)
    comp = BM.body_composition(weight, bf)

    latest_waist = db.scalar(
        select(WaistLog)
        .where(WaistLog.user_id == current_user.id)
        .order_by(WaistLog.date.desc(), WaistLog.created_at.desc())
        .limit(1)
    )

    return BodyMetricsOut(
        weight_kg=round(weight, 1),
        height_cm=profile.height_cm,
        bmi=round(bmi_val, 1),
        bmi_category_ar=BM.bmi_category_ar(bmi_val),
        healthy_min_kg=lo,
        healthy_max_kg=hi,
        body_fat_pct=bf,
        body_fat_method_ar="تقدير Deurenberg (حسب BMI والعمر والجنس)",
        fat_mass_kg=comp.fat_mass_kg,
        lean_mass_kg=comp.lean_mass_kg,
        waist_cm=latest_waist.waist_cm if latest_waist else None,
    )


@router.get("/streak", response_model=StreakOut)
def streak(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> StreakOut:
    """سلسلة أيام التسجيل المتتالية + الإنجازات — لتحفيز المستخدم على الاستمرار 🔥."""
    return StreakOut(**gamification.compute(db, current_user.id))


@router.get("/drinks/suggestions", response_model=list[DrinkSuggestion])
def drink_suggestions(current_user: User = Depends(get_current_user)):
    """اقتراح مشروبات تساعد (ماء/مشروبات قليلة السعرات)."""
    return [
        DrinkSuggestion(name_ar="ماء", approx_calories=0, note_ar="الأساس — جسمك بيحتاجه طول اليوم 💧"),
        DrinkSuggestion(name_ar="ماء بالليمون والنعناع", approx_calories=5, note_ar="منعش وبيكسر الملل من الماء العادي"),
        DrinkSuggestion(name_ar="شاي أخضر بدون سكر", approx_calories=2, note_ar="مشروب دافي خفيف"),
        DrinkSuggestion(name_ar="قهوة سادة", approx_calories=2, note_ar="بدون سكر ولا لبن"),
        DrinkSuggestion(name_ar="كركديه بارد بدون سكر", approx_calories=5, note_ar="منعش وقليل السعرات"),
        DrinkSuggestion(name_ar="مياه غازية بنكهة بدون سكر", approx_calories=0, note_ar="بديل حلو عن المشروبات الغازية العادية"),
    ]
