"""سكيمات المصادقة — تسجيل، دخول، رمز، وبيانات المستخدم."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="اسم المستخدم")
    password: str = Field(..., min_length=6, max_length=128, description="كلمة السر")

    @field_validator("username")
    @classmethod
    def _clean_username(cls, v: str) -> str:
        v = v.strip()
        if " " in v:
            raise ValueError("اسم المستخدم لا يحتوي على مسافات")
        if not v:
            raise ValueError("اسم المستخدم مطلوب")
        return v


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=30)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime
    has_profile: bool = False
