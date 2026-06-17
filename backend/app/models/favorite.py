"""المفضّلة — للإضافة السريعة لعناصر متكرّرة (من المكتبة أو وصفة أو عنصر مخصّص)."""
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .enums import FavoriteRefType


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "ref_type", "ref_id", "name_ar", name="uq_favorite_ref"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ref_type: Mapped[FavoriteRefType] = mapped_column(
        SAEnum(FavoriteRefType, native_enum=False, length=10), nullable=False
    )
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # id المكتبة/الوصفة إن وُجد
    name_ar: Mapped[str] = mapped_column(String(160), nullable=False)
    # قيم مخزّنة للإضافة السريعة (لكل الكمية الافتراضية أدناه)
    default_amount: Mapped[float] = mapped_column(Float, nullable=False, default=100)
    calories: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
