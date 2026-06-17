"""نماذج الوصفات — وصفة بمكوناتها وحساب نصيب الفرد بدقة."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name_ar: Mapped[str] = mapped_column(String(160), nullable=False)
    servings: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    # إجماليات الحلة بالكامل (مجموع المكونات)
    total_calories: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_protein: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_fat: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeIngredient.id"
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name_ar: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # بالجرام
    is_oil: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # زيت/سمنة
    # قيم المكوّن لكامل كميته
    calories: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")
