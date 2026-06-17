"""سكيمات مزامنة الصحة."""
from datetime import date as date_type

from pydantic import BaseModel, Field

from ..models.enums import ActivitySource


class HealthSyncIn(BaseModel):
    """دفع بيانات صحية مقروءة على الجهاز (هواوي/Health Connect/يدوي)."""

    date: date_type | None = None
    source: ActivitySource = ActivitySource.manual
    steps: int | None = Field(None, ge=0)
    active_minutes: int | None = Field(None, ge=0, le=1440)
    calories_burned: float | None = Field(None, ge=0)
    sleep_hours: float | None = Field(None, ge=0, le=24)
    activity_type_ar: str | None = Field(None, max_length=80)


class HealthSyncOut(BaseModel):
    date: date_type
    saved_activity: bool
    saved_sleep: bool
    steps: int | None
    calories_burned: float | None
    note_ar: str


class HealthStatusOut(BaseModel):
    huawei_configured: bool
    providers_priority_ar: list[str]
    note_ar: str


class HealthAuthorizeOut(BaseModel):
    authorize_url: str
    state: str
