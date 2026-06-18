"""اشتراك المستخدم المدفوع (Premium) — مصدر الحقيقة للصلاحية.

التفعيل يتم **دائماً** بعد تحقّق الخادم من Google Play (مش من العميل). نخزّن آخر
حالة معروفة للاشتراك ووقت انتهاء الفترة الحالية، ونحسب is_premium منهم.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

# حالات الاشتراك التي تُعتبر "مفعّلة" (تمنح الصلاحية)
ACTIVE_STATUSES = {"active", "in_grace_period"}


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="google_play")
    product_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # رمز الشراء — مفتاح idempotency؛ فريد لتفادي تكرار نفس الشراء
    purchase_token: Mapped[str | None] = mapped_column(String(512), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="none")
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    auto_renewing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="subscription")  # noqa: F821
