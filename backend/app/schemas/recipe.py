"""سكيمات الوصفات — البناء بمكونات (مع خانة الزيت) وحساب نصيب الفرد."""
from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..models.enums import Meal


class RecipeIngredientIn(BaseModel):
    """مكوّن — إما بقيم لكل 100جم أو بمرجع من المكتبة (library_id)."""

    name_ar: str | None = Field(None, max_length=160)
    amount_g: float = Field(..., gt=0)
    is_oil: bool = False
    library_id: int | None = None
    # قيم لكل 100 جرام (إن لم يُستخدم library_id)
    per100_calories: float | None = Field(None, ge=0)
    per100_protein: float | None = Field(None, ge=0)
    per100_carbs: float | None = Field(None, ge=0)
    per100_fat: float | None = Field(None, ge=0)

    @model_validator(mode="after")
    def _check_source(self):
        if self.library_id is None:
            if self.per100_calories is None or not self.name_ar:
                raise ValueError(
                    "كل مكوّن يحتاج إما library_id أو (name_ar + per100_calories)"
                )
        return self


class RecipeIn(BaseModel):
    name_ar: str = Field(..., min_length=1, max_length=160)
    servings: float = Field(1, gt=0, description="عدد الأنفار/الحصص")
    ingredients: list[RecipeIngredientIn] = Field(..., min_length=1)


class RecipeIngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name_ar: str
    amount: float
    is_oil: bool
    calories: float
    protein: float
    carbs: float
    fat: float


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name_ar: str
    servings: float
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    ingredients: list[RecipeIngredientOut]
    # نصيب الفرد (محسوب)
    per_serving_calories: float = 0
    per_serving_protein: float = 0
    per_serving_carbs: float = 0
    per_serving_fat: float = 0


class RecipeLogIn(BaseModel):
    """تسجيل نصيب من وصفة محفوظة."""

    date: date_type
    meal: Meal
    servings: float = Field(1, gt=0, description="عدد الأنفار المتناوَلة")
