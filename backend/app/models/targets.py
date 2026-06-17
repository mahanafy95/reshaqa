"""الأهداف اليومية — سعرات وماكروز كل يوم (تخسيس أو تثبيت)."""
from datetime import date

from sqlalchemy import Boolean, Date, Enum as SAEnum, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .enums import TargetMode


class DailyTarget(Base):
    __tablename__ = "daily_targets"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_target_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    mode: Mapped[TargetMode] = mapped_column(
        SAEnum(TargetMode, native_enum=False, length=10), nullable=False, default=TargetMode.loss
    )
    # هل وصل الهدف للحد الأدنى الآمن (لإظهار رسالة توضيحية)
    floored_to_safe_min: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
