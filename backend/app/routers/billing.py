"""راوتر الاشتراكات — تفعيل/حالة الاشتراك المدفوع عبر Google Play.

التفعيل دايماً بعد تحقّق الخادم من Play (مش من العميل). RTDN يحدّث الحالة فورياً.
"""
import base64
import json
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.billing import get_subscription, user_is_premium
from ..core.deps import get_current_user
from ..core.ratelimit import limiter
from ..database import get_db
from ..models.subscription import ACTIVE_STATUSES, Subscription
from ..models.user import User
from ..schemas.billing import BillingStatusOut, VerifyPurchaseRequest
from ..services import play_billing

logger = logging.getLogger("reshaqa.billing")
router = APIRouter(prefix="/billing", tags=["الاشتراكات"])


def _status_out(sub: Subscription | None) -> BillingStatusOut:
    if sub is None:
        return BillingStatusOut(is_premium=False, status="none")
    return BillingStatusOut(
        is_premium=user_is_premium(sub),
        status=sub.status,
        product_id=sub.product_id,
        current_period_end=sub.current_period_end,
        auto_renewing=sub.auto_renewing,
    )


@router.get("/status", response_model=BillingStatusOut)
def billing_status(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> BillingStatusOut:
    return _status_out(get_subscription(db, current_user.id))


@router.post("/google/verify", response_model=BillingStatusOut)
@limiter.limit("20/minute")
def verify_google_purchase(
    request: Request,
    payload: VerifyPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingStatusOut:
    """يتحقّق من رمز شراء Play ويفعّل الاشتراك للمستخدم الحالي."""
    info = play_billing.verify_purchase(payload.purchase_token)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="تعذّر التحقّق من الشراء. حاول تاني أو تواصل معانا.",
        )
    allowed = settings.play_product_ids_set
    if allowed and info.product_id and info.product_id not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="منتج غير معروف.")

    # امنع ربط نفس رمز الشراء بحساب تاني
    clash = db.scalar(
        select(Subscription).where(
            Subscription.purchase_token == payload.purchase_token,
            Subscription.user_id != current_user.id,
        )
    )
    if clash is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="الشراء ده مربوط بحساب تاني.")

    sub = get_subscription(db, current_user.id)
    if sub is None:
        sub = Subscription(user_id=current_user.id)
        db.add(sub)
    sub.platform = "google_play"
    sub.product_id = info.product_id or payload.product_id
    sub.purchase_token = payload.purchase_token
    sub.status = info.status
    sub.current_period_end = info.expiry
    sub.auto_renewing = info.auto_renewing
    db.commit()
    db.refresh(sub)

    # تأكيد الاستلام (مطلوب خلال 3 أيام وإلا يُسترجع تلقائياً)
    if info.status in ACTIVE_STATUSES and not info.acknowledged:
        play_billing.acknowledge_purchase(payload.purchase_token)

    return _status_out(sub)


class _PubSubEnvelope(BaseModel):
    message: dict | None = None
    subscription: str | None = None


@router.post("/google/rtdn", include_in_schema=False)
def play_rtdn(
    envelope: _PubSubEnvelope,
    token: str = Query("", description="رمز تحقّق Pub/Sub"),
    db: Session = Depends(get_db),
) -> dict:
    """ويبهوك Real-time Developer Notifications من Google Play (عبر Pub/Sub push).

    يحدّث حالة الاشتراك فور تغيّرها (تجديد/إلغاء/انتهاء). يرجّع 200 دائماً.
    """
    expected = settings.PUBSUB_VERIFICATION_TOKEN
    if not expected:
        # fail-closed في الإنتاج: لازم رمز تحقّق (في التطوير نسمح للاختبار المحلي)
        if settings.APP_ENV == "production":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    elif not secrets.compare_digest(token, expected):  # مقارنة ثابتة الزمن
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    try:
        data_b64 = (envelope.message or {}).get("data")
        if data_b64:
            payload = json.loads(base64.b64decode(data_b64))
            notif = payload.get("subscriptionNotification") or {}
            ptoken = notif.get("purchaseToken")
            if ptoken:
                sub = db.scalar(
                    select(Subscription).where(Subscription.purchase_token == ptoken)
                )
                if sub is not None:
                    info = play_billing.verify_purchase(ptoken)
                    if info is not None:
                        sub.status = info.status
                        sub.current_period_end = info.expiry
                        sub.auto_renewing = info.auto_renewing
                        db.commit()
    except Exception:
        logger.exception("فشل معالجة إشعار RTDN")
    return {"ok": True}
