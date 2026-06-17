"""سكيمات الملخص اليومي ومؤشرات الجسم واقتراح المشروبات."""
from datetime import date as date_type

from pydantic import BaseModel

from ..models.enums import Meal, TargetMode


class MacroStatus(BaseModel):
    name_ar: str            # سعرات | بروتين | نشويات | دهون
    target: float
    eaten: float
    remaining: float
    status: str             # مظبوط | قليل | كتير
    message_ar: str


class MealBreakdown(BaseModel):
    meal: Meal
    calories: float
    protein: float
    carbs: float
    fat: float


class DailySummaryOut(BaseModel):
    date: date_type
    mode: TargetMode
    target_calories: float
    eaten_calories: float
    remaining_calories: float
    percent_of_target: int
    calories_status: MacroStatus
    macros: list[MacroStatus]               # بروتين/نشويات/دهون
    meals: list[MealBreakdown]
    encouragement_ar: str
    activity_note_ar: str = "النشاط بيتسجّل لوحده وما بيتخصمش من ميزانية الأكل."


class BodyMetricsOut(BaseModel):
    weight_kg: float
    height_cm: float
    bmi: float
    bmi_category_ar: str
    healthy_min_kg: float
    healthy_max_kg: float
    body_fat_pct: float | None
    body_fat_method_ar: str
    fat_mass_kg: float | None
    lean_mass_kg: float | None
    waist_cm: float | None = None
    note_ar: str = "القيم تقديرية للتوعية وليست تشخيصاً طبياً."


class DrinkSuggestion(BaseModel):
    name_ar: str
    approx_calories: int
    note_ar: str
