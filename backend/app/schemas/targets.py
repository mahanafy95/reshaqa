"""سكيمات الأهداف اليومية ونتيجة المحرك."""
from datetime import date

from pydantic import BaseModel, ConfigDict

from ..models.enums import TargetMode


class MacrosOut(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class PlateauOut(BaseModel):
    is_plateau: bool
    weeks_considered: float
    net_change_kg: float
    slope_kg_per_week: float | None
    message_ar: str = ""


class TargetOut(BaseModel):
    """نتيجة حساب الأهداف الحالية (محسوبة من أحدث وزن)."""

    bmr: float
    tdee: float
    mode: TargetMode
    target_calories: float
    deficit_applied: float  # موجب = عجز (تخسيس)، سالب = فائض (زيادة)
    floored_to_safe_min: bool
    macros: MacrosOut
    bmi: float
    weight_status: str = "normal"  # underweight | normal | overweight
    recommended_goal_weight_kg: float | None = None
    current_weight_kg: float
    messages_ar: list[str] = []
    plateau: PlateauOut | None = None


class DailyTargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    mode: TargetMode
    floored_to_safe_min: bool
