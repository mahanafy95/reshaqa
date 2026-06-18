"""المجتمع — الصداقات والرسائل (أصدقاء يضيفوا بعض ويشجّعوا بعض)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Friendship(Base):
    """علاقة صداقة بين مستخدمين — صف واحد (الطالب + المُستقبِل) بحالة."""
    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
        Index("ix_friendship_addressee_status", "addressee_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    addressee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending")  # pending | accepted
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Message(Base):
    """رسالة بين صديقين (نص أو تشجيع)."""
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_message_pair_time", "sender_id", "recipient_id", "created_at"),
        Index("ix_message_recipient_unread", "recipient_id", "read_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    body: Mapped[str] = mapped_column(String(2000), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="text")  # text | cheer
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
