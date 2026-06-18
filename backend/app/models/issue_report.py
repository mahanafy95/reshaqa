"""بلاغات المشاكل — أي مستخدم مسجّل يبعت مشكلة نصية والمشرف يراجعها لاحقاً."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class IssueReport(Base):
    """بلاغ مشكلة مرسَل من مستخدم — يبدأ بحالة 'new' ويراجعه المشرف."""
    __tablename__ = "issue_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new"
    )  # new | seen | resolved
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
