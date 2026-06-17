"""نموذج توكن مزامنة الصحة (هواوي / Health Connect) لكل مستخدم."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class HealthToken(Base):
    """توكن OAuth لمزوّد صحة (للمزامنة من جهة الخادم عند تهيئة الـ credentials)."""

    __tablename__ = "health_tokens"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_health_token_user_provider"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # huawei | health_connect
    access_token: Mapped[str] = mapped_column(String(2048), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(512), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
