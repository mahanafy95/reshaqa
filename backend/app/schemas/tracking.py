"""سكيمات المتابعة — الوزن، الوسط، المياه، النشاط، الحالة المزاجية."""
from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import ActivitySource


# ---------- الوزن ----------
class WeightIn(BaseModel):
    date: date_type | None = None  # افتراضياً اليوم
    weight_kg: float = Field(..., ge=20, le=400)


class WeightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    weight_kg: float
    created_at: datetime


class TrendPointOut(BaseModel):
    day: date_type
    raw_kg: float
    trend_kg: float


class PlateauInfo(BaseModel):
    is_plateau: bool
    weeks_considered: float
    net_change_kg: float
    slope_kg_per_week: float | None
    message_ar: str = ""


class WeightTrendOut(BaseModel):
    points: list[TrendPointOut]
    current_trend_kg: float | None
    slope_kg_per_week: float | None
    plateau: PlateauInfo | None
    suggested_weigh_in_day_ar: str = "الجمعة"
    note_ar: str = "بنتابع وزنك بالاتجاه (المتوسط) مش الرقم اليومي، لأن الوزن بيتذبذب طبيعي."


# ---------- الوسط (اختياري ومنفصل) ----------
class WaistIn(BaseModel):
    date: date_type | None = None
    waist_cm: float = Field(..., ge=30, le=250)


class WaistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    waist_cm: float
    created_at: datetime


# ---------- المياه ----------
class WaterIn(BaseModel):
    date: date_type | None = None
    ml: int = Field(..., gt=0, le=3000)


class WaterDayOut(BaseModel):
    date: date_type
    total_ml: int
    goal_ml: int
    remaining_ml: int
    percent: int
    message_ar: str = ""


# ---------- النشاط (منفصل، لا يُحسب على ميزانية الأكل) ----------
class ActivityIn(BaseModel):
    date: date_type | None = None
    type_ar: str = Field(..., min_length=1, max_length=80)
    duration_min: int = Field(0, ge=0, le=1440)
    calories_burned: float | None = Field(None, ge=0)
    steps: int | None = Field(None, ge=0)
    source: ActivitySource = ActivitySource.manual


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    type_ar: str
    duration_min: int
    calories_burned: float | None
    steps: int | None
    source: ActivitySource
    created_at: datetime


# ---------- الحالة المزاجية ----------
class MoodIn(BaseModel):
    date: date_type | None = None
    energy: int | None = Field(None, ge=1, le=5)
    sleep_hours: float | None = Field(None, ge=0, le=24)
    hunger: int | None = Field(None, ge=1, le=5)


class MoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    energy: int | None
    sleep_hours: float | None
    hunger: int | None
