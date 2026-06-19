"""نموذج رسائل المساعد الذكي — لحفظ المحادثة (تستمر بين الجلسات وعبر الأجهزة)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class AssistantMessage(Base):
    """رسالة واحدة في محادثة المستخدم مع المساعد الصحي الذكي (user أو assistant)."""

    __tablename__ = "assistant_messages"
    __table_args__ = (
        Index("ix_assistant_messages_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
