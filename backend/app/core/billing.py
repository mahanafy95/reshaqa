"""منطق الصلاحية المدفوعة (Premium) + تبعية حماية الميزات المميّزة.

is_premium يُحسب من حالة الاشتراك المخزّنة (التي يحدّثها الخادم بعد تحقّق Play).
require_premium ترجع 402 برسالة ترقية ودّية للمستخدم المجاني (مش رسالة خطأ).
"""
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.subscription import ACTIVE_STATUSES, Subscription
from ..models.user import User
from .deps import get_current_user

# 402 Payment Required — كود مناسب لـ "محتاج اشتراك"
PREMIUM_REQUIRED = status.HTTP_402_PAYMENT_REQUIRED
_UPSELL = {
    "message": "دي ميزة مميّزة (Premium) ✨ اشترك عشان تفتحها وتستمتع بكل المميزات 💎",
    "premium_required": True,
}


def user_is_premium(sub: Subscription | None) -> bool:
    """هل المستخدم مشترك فعّال الآن؟"""
    if sub is None or sub.status not in ACTIVE_STATUSES:
        return False
    end = sub.current_period_end
    if end is None:
        return True
    if end.tzinfo is None:  # SQLite قد يرجّعه بدون منطقة زمنية
        end = end.replace(tzinfo=timezone.utc)
    return end > datetime.now(timezone.utc)


def get_subscription(db: Session, user_id: int) -> Subscription | None:
    return db.scalar(select(Subscription).where(Subscription.user_id == user_id))


def is_user_premium(db: Session, user_id: int) -> bool:
    return user_is_premium(get_subscription(db, user_id))


def require_premium(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    """تحمي الميزات المدفوعة — ترفع 402 مع رسالة ترقية لو المستخدم مش مشترك."""
    if not is_user_premium(db, current_user.id):
        raise HTTPException(status_code=PREMIUM_REQUIRED, detail=_UPSELL)
    return current_user
