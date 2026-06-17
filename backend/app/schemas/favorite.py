"""سكيمات المفضّلة — للإضافة السريعة."""
from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..models.enums import FavoriteRefType, Meal


class FavoriteIn(BaseModel):
    """إنشاء مفضّلة — من المكتبة (library_id) أو وصفة (recipe_id) أو قيم مخصّصة."""

    ref_type: FavoriteRefType
    library_id: int | None = None
    recipe_id: int | None = None
    name_ar: str | None = Field(None, max_length=160)
    default_amount: float = Field(100, gt=0)
    # للعنصر المخصّص (custom) — القيم الإجمالية للكمية الافتراضية
    calories: float | None = Field(None, ge=0)
    protein: float | None = Field(None, ge=0)
    carbs: float | None = Field(None, ge=0)
    fat: float | None = Field(None, ge=0)

    @model_validator(mode="after")
    def _check(self):
        if self.ref_type == FavoriteRefType.library and self.library_id is None:
            raise ValueError("library مفضّلة تحتاج library_id")
        if self.ref_type == FavoriteRefType.recipe and self.recipe_id is None:
            raise ValueError("recipe مفضّلة تحتاج recipe_id")
        if self.ref_type == FavoriteRefType.custom and (
            not self.name_ar or self.calories is None
        ):
            raise ValueError("custom مفضّلة تحتاج name_ar و calories")
        return self


class FavoriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ref_type: FavoriteRefType
    ref_id: int | None
    name_ar: str
    default_amount: float
    calories: float
    protein: float
    carbs: float
    fat: float


class FavoriteLogIn(BaseModel):
    date: date_type
    meal: Meal
    amount: float | None = Field(None, gt=0, description="الكمية (افتراضياً default_amount)")
