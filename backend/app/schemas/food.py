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
    source: str = "barcode"  # local | barcode (Open Food Facts) | contributed


class BarcodeIn(BaseModel):
    """حفظ منتج بالباركود في المكتبة (مساهمة المستخدم — يتعرّف عليه بعد كده)."""
    barcode: str = Field(..., min_length=6, max_length=20)
    name_ar: str = Field(..., min_length=1, max_length=120)
    calories_per_100: float = Field(..., ge=0, le=2000)
    protein: float = Field(0, ge=0, le=200)
    carbs: float = Field(0, ge=0, le=300)
    fat: float = Field(0, ge=0, le=200)
    household_unit_ar: str | None = Field(None, max_length=40)
    household_grams: float | None = Field(None, gt=0, le=5000)


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


# ---------- المحلّل الذكي (اكتب أكلك بالكلام) ----------
class ParsedFoodItem(BaseModel):
    name_ar: str
    qty: float
    unit: str | None = None
    grams: float
    meal: Meal
    calories: float
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    confidence: str = "medium"  # high | medium | low
    source: FoodSource = FoodSource.estimated
    matched_library_id: int | None = None
    note_ar: str = ""


class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    date: date_type = Field(default_factory=date_type.today)
    default_meal: Meal = Meal.snack
    confirm: bool = False

    _v_date = field_validator("date")(validate_log_date)


class ParseResponse(BaseModel):
    items: list[ParsedFoodItem] = []
    total_calories: float = 0
    logged: bool = False
    logged_ids: list[int] = []
    reply_ar: str = ""
