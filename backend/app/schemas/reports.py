"""سكيمات التقارير الأسبوعية والشهرية (مفصّلة)."""
from datetime import date as date_type

from pydantic import BaseModel, ConfigDict


class DayAdherenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date_type
    target_calories: float
    eaten_calories: float
    protein: float
    carbs: float
    fat: float
    status: str


class WeeklyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start: date_type
    end: date_type
    days: list[DayAdherenceOut]
    adherent_days: int
    logged_days: int
    days_within: int
    days_over: int
    days_under: int
    avg_eaten: float
    avg_target: float
    avg_protein: float
    avg_carbs: float
    avg_fat: float
    best_day: date_type | None
    water_avg_ml: int
    activity_total_min: int
    activity_total_calories: int
    activity_sessions: int
    weight_change_kg: float | None
    weight_slope_kg_week: float | None
    mode: str = "loss"
    weight_status: str = "normal"
    summary_ar: str


class MonthlyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year: int
    month: int
    start: date_type
    end: date_type
    weeks: list[WeeklyReportOut]
    total_adherent_days: int
    total_logged_days: int
    avg_eaten: float
    avg_protein: float
    avg_carbs: float
    avg_fat: float
    water_avg_ml: int
    activity_total_min: int
    activity_total_calories: int
    weight_change_kg: float | None
    mode: str = "loss"
    weight_status: str = "normal"
    summary_ar: str
