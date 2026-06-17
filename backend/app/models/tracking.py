"""نماذج المتابعة — الوزن، الوسط، المياه، النشاط، والحالة المزاجية.

ملاحظات مهمة:
- مقاس الوسط منفصل واختياري (لا يلزم مع كل وزن).
- النشاط منفصل ولا يُحسب على ميزانية الأكل (السعرات المحروقة تُعرض كنشاط فقط).
"""
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .enums import ActivitySource


class WeightLog(Base):
    """تسجيل الوزن — قد يكون أكثر من تسجيل، والمتابعة بالاتجاه (موفينج آفريج)."""

    __tablename__ = "weight_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WaistLog(Base):
    """مقاس الوسط — اختياري ومنفصل تماماً عن الوزن."""

    __tablename__ = "waist_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    waist_cm: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WaterLog(Base):
    """تسجيل شرب الماء — كل إدخال بالمليلتر (يُجمَّع يومياً)."""

    __tablename__ = "water_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ml: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ActivityLog(Base):
    """تسجيل النشاط — منفصل، لا يُحسب على ميزانية الأكل."""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    type_ar: Mapped[str] = mapped_column(String(80), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # سعرات محروقة تقديرية — للعرض كنشاط فقط (لا تُردّ على ميزانية الأكل)
    calories_burned: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[ActivitySource] = mapped_column(
        SAEnum(ActivitySource, native_enum=False, length=20),
        nullable=False,
        default=ActivitySource.manual,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MoodLog(Base):
    """"حاسس بإيه النهاردة" — الطاقة والنوم والجوع."""

    __tablename__ = "mood_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)       # 1..5
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    hunger: Mapped[int | None] = mapped_column(Integer, nullable=True)       # 1..5
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
