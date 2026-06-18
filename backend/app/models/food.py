"""نماذج الأكل — مكتبة الأكلات والأكل المسجّل يومياً."""
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .enums import FoodSource, Meal, Region


class FoodLibrary(Base):
    """مكتبة أكلات عامة (قيمها لكل 100 جرام) — أكلات مصرية وسعودية وعامة."""

    __tablename__ = "food_library"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    # باركود المنتج (اختياري) — للبحث بالمسح. القيم لكل 100 جرام/مل
    barcode: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    # القيم لكل 100 جرام
    calories_per_100: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    region: Mapped[Region] = mapped_column(
        SAEnum(Region, native_enum=False, length=10), nullable=False, default=Region.generic
    )
    # وحدة منزلية تقريبية اختيارية (مثل: رغيف، كوب، ملعقة) ووزنها بالجرام
    household_unit_ar: Mapped[str | None] = mapped_column(String(40), nullable=True)
    household_grams: Mapped[float | None] = mapped_column(Float, nullable=True)


class FoodLogged(Base):
    """عنصر أكل مسجّل في يوم معيّن لمستخدم (القيم نهائية للكمية المُدخلة)."""

    __tablename__ = "foods_logged"
    __table_args__ = (
        Index("ix_foods_logged_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    meal: Mapped[Meal] = mapped_column(SAEnum(Meal, native_enum=False, length=12), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # الكمية بالجرام (أو حسب الوحدة)
    # القيم الإجمالية للكمية المسجّلة (وليست لكل 100 جرام)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    source: Mapped[FoodSource] = mapped_column(
        SAEnum(FoodSource, native_enum=False, length=12), nullable=False, default=FoodSource.manual
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
