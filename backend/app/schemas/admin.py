"""سكيمات لوحة الإشراف (سوبر أدمن)."""
from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _clean_username(v: str) -> str:
    v = v.strip()
    if " " in v:
        raise ValueError("اسم المستخدم لا يحتوي على مسافات")
    if not v:
        raise ValueError("اسم المستخدم مطلوب")
    return v


class AdminProfileOut(BaseModel):
    age: int | None = None
    sex: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    activity_level: str | None = None
    goal_weight_kg: float | None = None
    goal_rate: float | None = None


class AdminUserSummary(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime
    has_profile: bool
    current_weight_kg: float | None = None
    goal_weight_kg: float | None = None
    target_calories: int | None = None
    foods_count: int = 0
    weights_count: int = 0
    last_food_date: date_type | None = None


class AdminFoodOut(BaseModel):
    date: date_type
    meal: str
    name_ar: str
    amount: float
    calories: float


class AdminWeightOut(BaseModel):
    date: date_type
    weight_kg: float


class AdminUserDetail(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime
    profile: AdminProfileOut | None = None
    target_calories: int | None = None
    bmi: float | None = None
    foods_count: int = 0
    weights_count: int = 0
    recent_foods: list[AdminFoodOut] = []
    recent_weights: list[AdminWeightOut] = []


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


class AdminCreateUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=128)
    is_admin: bool = False

    _v_username = field_validator("username")(_clean_username)


class ChangeUsernameRequest(BaseModel):
    new_username: str = Field(..., min_length=3, max_length=30)

    _v_username = field_validator("new_username")(_clean_username)


class SetAdminRequest(BaseModel):
    is_admin: bool


class AdminActionResult(BaseModel):
    ok: bool = True
    message: str
