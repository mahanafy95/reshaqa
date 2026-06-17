"""سكيمات الملف الشخصي."""
from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import ActivityLevel, Sex


class ProfileIn(BaseModel):
    age: int = Field(..., ge=10, le=100, description="العمر بالسنوات")
    sex: Sex
    height_cm: float = Field(..., ge=100, le=250)
    weight_kg: float = Field(..., ge=30, le=400)
    activity_level: ActivityLevel
    goal_weight_kg: float | None = Field(None, ge=30, le=400)
    goal_rate: float | None = Field(
        None, ge=0.1, le=1.5, description="معدل النزول المطلوب (كجم/أسبوع)"
    )


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    age: int
    sex: Sex
    height_cm: float
    weight_kg: float
    activity_level: ActivityLevel
    goal_weight_kg: float | None
    goal_rate: float | None
    healthy_min_kg: float = 0
    healthy_max_kg: float = 0
