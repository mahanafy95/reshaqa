"""سكيمات التقارير الأسبوعية والشهرية."""
from datetime import date as date_type

from pydantic import BaseModel, ConfigDict


class DayAdherenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date_type
    target_calories: float
    eaten_calories: float
    status: str


class WeeklyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start: date_type
    end: date_type
    days: list[DayAdherenceOut]
    adherent_days: int
    logged_days: int
    avg_eaten: float
    avg_target: float
    weight_change_kg: float | None
    weight_slope_kg_week: float | None
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
    weight_change_kg: float | None
    summary_ar: str
