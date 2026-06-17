"""سكيمات تسجيل الأكل والمكتبة والتقدير والباركود والملصق."""
from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.enums import FoodSource, Meal, Region
from ._common import validate_log_date


class FoodLogIn(BaseModel):
    date: date_type
    meal: Meal
    name_ar: str = Field(..., min_length=1, max_length=160)
    amount: float = Field(..., gt=0, allow_inf_nan=False)
    calories: float = Field(..., ge=0, allow_inf_nan=False)
    protein: float = Field(0, ge=0, allow_inf_nan=False)
    carbs: float = Field(0, ge=0, allow_inf_nan=False)
    fat: float = Field(0, ge=0, allow_inf_nan=False)
    source: FoodSource = FoodSource.manual

    _v_date = field_validator("date")(validate_log_date)


class FoodLogUpdate(BaseModel):
    """تعديل جزئي — كل الحقول اختيارية (تعديل الرقم يدوياً مدعوم)."""

    meal: Meal | None = None
    name_ar: str | None = Field(None, min_length=1, max_length=160)
    amount: float | None = Field(None, gt=0, allow_inf_nan=False)
    calories: float | None = Field(None, ge=0, allow_inf_nan=False)
    protein: float | None = Field(None, ge=0, allow_inf_nan=False)
    carbs: float | None = Field(None, ge=0, allow_inf_nan=False)
    fat: float | None = Field(None, ge=0, allow_inf_nan=False)


class FoodLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    meal: Meal
    name_ar: str
    amount: float
    calories: float
    protein: float
    carbs: float
    fat: float
    source: FoodSource
    created_at: datetime


class FoodLibraryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name_ar: str
    calories_per_100: float
    protein: float
    carbs: float
    fat: float
    region: Region
    household_unit_ar: str | None = None
    household_grams: float | None = None


class EstimateOut(BaseModel):
    name_ar: str
    amount_g: float
    calories: float
    protein: float
    carbs: float
    fat: float
    per100_calories: float
    confidence: str
    note_ar: str
    source: FoodSource


class BarcodeOut(BaseModel):
    barcode: str
    name_ar: str
    calories_per_100: float
    protein: float
    carbs: float
    fat: float


class LabelParseOut(BaseModel):
    calories: float | None
    protein: float | None
    carbs: float | None
    fat: float | None
    basis_ar: str
    note_ar: str = ""


class SuggestionOut(BaseModel):
    """اقتراح عند كتابة اسم أكلة — من المكتبة أو الوصفات أو المفضلة."""

    kind: str            # library | recipe | favorite
    ref_id: int
    name_ar: str
    calories_per_100: float | None = None    # للمكتبة (لكل 100جم)
    calories_per_serving: float | None = None  # للوصفة (نصيب الفرد)
    region: Region | None = None
