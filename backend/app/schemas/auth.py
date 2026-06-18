"""سكيمات المصادقة — تسجيل، دخول، جوجل، إعادة تعيين كلمة السر، وبيانات المستخدم."""
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# تحقّق بسيط من صيغة البريد بدون تبعية email-validator (نبقى خفاف وبدون حزم إضافية)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_email_optional(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip().lower()
    if not v:
        return None
    if not _EMAIL_RE.match(v) or len(v) > 255:
        raise ValueError("صيغة البريد الإلكتروني غير صحيحة")
    return v


def _clean_email_required(v: str) -> str:
    cleaned = _clean_email_optional(v)
    if cleaned is None:
        raise ValueError("البريد الإلكتروني مطلوب")
    return cleaned


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="اسم المستخدم")
    password: str = Field(..., min_length=6, max_length=128, description="كلمة السر")
    email: str | None = Field(None, max_length=255, description="البريد (اختياري — لإعادة تعيين كلمة السر)")

    @field_validator("username")
    @classmethod
    def _clean_username(cls, v: str) -> str:
        v = v.strip()
        if " " in v:
            raise ValueError("اسم المستخدم لا يحتوي على مسافات")
        if not v:
            raise ValueError("اسم المستخدم مطلوب")
        return v

    @field_validator("email")
    @classmethod
    def _v_email(cls, v: str | None) -> str | None:
        return _clean_email_optional(v)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=30)
    password: str = Field(..., min_length=1, max_length=128)


class GoogleAuthRequest(BaseModel):
    """رمز الهوية (ID token) الصادر من جوجل على العميل."""
    id_token: str = Field(..., min_length=10, max_length=5000)


class SetEmailRequest(BaseModel):
    email: str = Field(..., max_length=255)

    @field_validator("email")
    @classmethod
    def _v_email(cls, v: str) -> str:
        return _clean_email_required(v)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., max_length=255)

    @field_validator("email")
    @classmethod
    def _v_email(cls, v: str) -> str:
        return _clean_email_required(v)


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., max_length=255)
    code: str = Field(..., min_length=4, max_length=10, description="الرمز المُرسل بالبريد")
    new_password: str = Field(..., min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def _v_email(cls, v: str) -> str:
        return _clean_email_required(v)

    @field_validator("code")
    @classmethod
    def _v_code(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("الرمز يتكوّن من أرقام فقط")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    created_at: datetime
    has_profile: bool = False
    is_admin: bool = False
    is_premium: bool = False
