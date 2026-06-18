"""راوتر مزامنة الصحة — هواوي (أولوية) ثم Health Connect ثم اليدوي."""
import secrets
from datetime import date as date_type
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.billing import require_premium
from ..core.deps import get_current_user
from ..database import get_db
from ..models.health import HealthToken
from ..models.tracking import ActivityLog
from ..models.user import User
from ..schemas.health import (
    HealthAuthorizeOut,
    HealthStatusOut,
    HealthSyncIn,
    HealthSyncOut,
)
from ..schemas.tracking import ActivityOut
from ..services import health_sync

router = APIRouter(prefix="/health", tags=["مزامنة الصحة"])


@router.get("/status", response_model=HealthStatusOut)
def health_status(current_user: User = Depends(get_current_user)):
    return HealthStatusOut(
        huawei_configured=health_sync.huawei_configured(),
        providers_priority_ar=["هواوي الصحة", "Android Health Connect", "إدخال يدوي"],
        note_ar=(
            "الأولوية لهواوي الصحة. لو مش متاح، التطبيق يستخدم Health Connect، "
            "وإلا الإدخال اليدوي. السعرات المحروقة للعرض فقط ولا تُخصم من ميزانية الأكل."
        ),
    )


@router.get("/huawei/authorize", response_model=HealthAuthorizeOut)
def huawei_authorize(current_user: User = Depends(get_current_user)):
    """يبني رابط موافقة هواوي (يتطلب تهيئة الـ credentials)."""
    state = secrets.token_urlsafe(16)
    url = health_sync.build_huawei_authorize_url(state)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "ربط هواوي غير مُهيّأ على الخادم. اضبط HUAWEI_HEALTH_CLIENT_ID و"
                "HUAWEI_HEALTH_REDIRECT_URI (راجع README لخطوات تسجيل المطوّر)."
            ),
        )
    return HealthAuthorizeOut(authorize_url=url, state=state)


@router.get("/huawei/callback")
def huawei_callback(
    code: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يبادل كود هواوي بتوكن ويخزّنه (عند تهيئة الـ credentials)."""
    token = health_sync.exchange_huawei_code(code)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذّر تبادل التوكن مع هواوي (غير مُهيّأ أو خطأ). جرّب المزامنة من الجهاز.",
        )
    existing = db.scalar(
        select(HealthToken).where(
            HealthToken.user_id == current_user.id, HealthToken.provider == "huawei"
        )
    )
    if existing is None:
        existing = HealthToken(user_id=current_user.id, provider="huawei")
        db.add(existing)
    existing.access_token = token.get("access_token", "")
    existing.refresh_token = token.get("refresh_token")
    if token.get("expires_in"):
        existing.expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(token["expires_in"]))
    existing.scope = token.get("scope")
    db.commit()
    return {"status": "linked", "message_ar": "تم ربط حساب هواوي بنجاح ✅"}


@router.post("/sync", response_model=HealthSyncOut, status_code=status.HTTP_201_CREATED)
def sync_health(
    payload: HealthSyncIn,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """يستقبل بيانات صحية مقروءة على الجهاز ويخزّنها (نشاط + نوم)."""
    day = payload.date or date_type.today()
    result = health_sync.apply_health_data(
        db,
        current_user.id,
        day=day,
        source=payload.source,
        steps=payload.steps,
        active_minutes=payload.active_minutes,
        calories_burned=payload.calories_burned,
        sleep_hours=payload.sleep_hours,
        activity_type_ar=payload.activity_type_ar,
    )
    return HealthSyncOut(
        date=result.date,
        saved_activity=result.saved_activity,
        saved_sleep=result.saved_sleep,
        steps=result.steps,
        calories_burned=result.calories_burned,
        note_ar=result.note_ar,
    )


@router.get("/data", response_model=list[ActivityOut])
def synced_activity(
    on: date_type | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """النشاط المُزامَن/المُسجّل لليوم (من أي مصدر)."""
    day = on or date_type.today()
    return db.scalars(
        select(ActivityLog)
        .where(ActivityLog.user_id == current_user.id, ActivityLog.date == day)
        .order_by(ActivityLog.created_at)
    ).all()
