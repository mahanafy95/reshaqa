"""الملف الشخصي للمستخدم — بيانات الجسم والهدف (أساس حساب السعرات)."""
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import ActivityLevel, Sex


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    sex: Mapped[Sex] = mapped_column(SAEnum(Sex, native_enum=False, length=10), nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    activity_level: Mapped[ActivityLevel] = mapped_column(
        SAEnum(ActivityLevel, native_enum=False, length=20), nullable=False
    )
    # الهدف (اختياري — قد لا يُحدّد المستخدم وزناً مستهدفاً بعد)
    goal_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    goal_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # كجم/أسبوع

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="profile")  # noqa: F821
