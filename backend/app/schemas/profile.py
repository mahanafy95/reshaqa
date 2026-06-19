"""سكيمات الملف الشخصي."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import ActivityLevel, Sex

DietaryPref = Literal["none", "halal", "vegetarian", "vegan", "keto", "low_carb"]


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
    dietary_pref: DietaryPref = "none"
    allergies: str | None = Field(None, max_length=200)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    age: int
    sex: Sex
    height_cm: float
    weight_kg: float
    activity_level: ActivityLevel
    goal_weight_kg: float | None
    goal_rate: float | None
    dietary_pref: str = "none"
    allergies: str | None = None
    healthy_min_kg: float = 0
    healthy_max_kg: float = 0
    weight_status: str = "normal"  # underweight | normal | overweight
    recommended_goal_weight_kg: float | None = None
